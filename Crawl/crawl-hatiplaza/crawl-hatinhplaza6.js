const puppeteer = require('puppeteer');
const cheerio = require('cheerio');
const XLSX = require('xlsx');
const fs = require('fs');

(async () => {
  try {
    const fileName = 'hatiplaza6.xlsx';

    let results = [];

    if (fs.existsSync(fileName)) {
      console.log(`Đã tìm thấy file [${fileName}]. Đọc dữ liệu cũ...`);
      const oldWorkbook = XLSX.readFile(fileName);
      const sheetName = oldWorkbook.SheetNames[0];
      const oldWorksheet = oldWorkbook.Sheets[sheetName];
      const oldData = XLSX.utils.sheet_to_json(oldWorksheet, { defval: '' });
      results = results.concat(oldData);
      console.log(`Đọc được ${oldData.length} dòng dữ liệu cũ.`);
    } else {
      console.log(`Không thấy file [${fileName}], sẽ tạo file mới sau khi crawl.`);
    }

    const browser = await puppeteer.launch({ headless: true });
    const page = await browser.newPage();

    const totalPages = 1;

    for (let pageIndex = 1; pageIndex <= totalPages; pageIndex++) {
      let url = `https://hatiplaza.com/mua-sam/danh-muc/do-gia-dung_214/?sort_by=newest`;
      console.log(`\n--- Đang crawl trang ${pageIndex} => ${url} ---`);

      await page.goto(url, { waitUntil: 'networkidle2', timeout: 60000 });
      const html = await page.content();
      const $ = cheerio.load(html);

      const pageData = [];

      $('li.p-item').each((i, el) => {
        let anchor = $(el).find('a');
        let rawHref = anchor.attr('href') || '';
        let detailURL = 'https://hatiplaza.com' + rawHref;

        let productName = $(el).find('.p-name').text().trim();

        pageData.push({
          productName,
          detailURL
        });
      });

      console.log(`   -> Thu được ${pageData.length} sản phẩm tại trang ${pageIndex}.`);

      for (let item of pageData) {
        let retries = 3;
        let success = false;

        while (retries > 0 && !success) {
          try {
            console.log(`     ... Đang vào chi tiết: ${item.detailURL}`);
            await page.goto(item.detailURL, { waitUntil: 'networkidle2', timeout: 60000 });
            let detailHtml = await page.content();
            let $detail = cheerio.load(detailHtml);

            let donViSanXuat = '';
            let diaChi = '';
            let sdt = '';
            let moTa = '';

            $detail('.product-desc p').each((idx, pEl) => {
              let lineText = $detail(pEl).text().trim();

              if (lineText.includes('Đơn vị sản xuất')) {
                let dvSplit = lineText.split('Đơn vị sản xuất:');
                let dvLeft = dvSplit[1] || '';
                if (dvLeft.includes('Địa chỉ:')) {
                  let ddSplit = dvLeft.split('Địa chỉ:');
                  donViSanXuat = ddSplit[0].trim();
                  diaChi = ddSplit[1] ? ddSplit[1].trim() : '';
                } else {
                  donViSanXuat = dvLeft.trim();
                }
              }
              if (lineText.includes('SĐT:')) {
                sdt = lineText.replace('- SĐT:', '').replace('SĐT:', '').trim();
              }
            });

            moTa = $detail('.product-detail').text().trim();

            results.push({
              'Link chi tiết': item.detailURL,
              'Tên sản phẩm': item.productName,
              'Đơn vị sản xuất': donViSanXuat,
              'Địa chỉ': diaChi,
              'SĐT': sdt,
              'Mô tả': moTa
            });

            success = true;
          } catch (detailErr) {
            console.error(`Lỗi khi vào ${item.detailURL}:`, detailErr.message);
            retries--;
            if (retries > 0) {
              console.log('     -> Thử lại sau 3 giây...');
              await page.waitForTimeout(3000);
            } else {
              console.log('     -> Bỏ qua sản phẩm này sau 3 lần thử thất bại.');
            }
          }
        }
      }

      const newWorkbook = XLSX.utils.book_new();
      const newWorksheet = XLSX.utils.json_to_sheet(results);
      XLSX.utils.book_append_sheet(newWorkbook, newWorksheet, 'OCOP-HaTinh');
      XLSX.writeFile(newWorkbook, fileName);

      console.log(`   -> Đã ghi tạm dữ liệu (tổng ${results.length} sp) vào [${fileName}].`);
    }

    await browser.close();
    console.log(`\nHoàn tất! Tổng sản phẩm thu được: ${results.length}.`);

  } catch (error) {
    console.error('Lỗi xảy ra:', error);
  }
})();

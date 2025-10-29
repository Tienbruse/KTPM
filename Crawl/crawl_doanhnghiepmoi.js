const puppeteer = require('puppeteer');
const cheerio = require('cheerio');
const XLSX = require('xlsx');
const fs = require('fs');

(async () => {
  try {
    // Tên file Excel
    const fileName = 'data-doanh-nghiep-ha-tinh.xlsx';
    // Mảng lưu dữ liệu chung
    let results = [];

    // 1) Kiểm tra nếu file Excel đã tồn tại
    if (fs.existsSync(fileName)) {
      console.log(`Đã tìm thấy file [${fileName}]. Đọc dữ liệu cũ để nối tiếp...`);
      // Đọc workbook cũ
      const oldWorkbook = XLSX.readFile(fileName);
      // Giả sử sheet tên "HaTinh"
      const sheetName = oldWorkbook.SheetNames[0];
      const oldWorksheet = oldWorkbook.Sheets[sheetName];
      // Chuyển sheet cũ -> mảng object
      const oldData = XLSX.utils.sheet_to_json(oldWorksheet, { defval: '' });
      // Ghép dữ liệu cũ vào results
      results = results.concat(oldData);
      console.log(`Đã đọc được ${oldData.length} dòng dữ liệu cũ.`);
    } else {
      console.log(`Không tìm thấy file [${fileName}], sẽ tạo file mới sau khi crawl.`);
    }

    // 2) Mở trình duyệt Puppeteer
    const browser = await puppeteer.launch({ headless: true });
    const page = await browser.newPage();

    // Giả sử ta sẽ crawl 5 trang
    const totalPages = 700;

    for (let pageIndex = 1; pageIndex <= totalPages; pageIndex++) {
      // Tạo URL trang
      let url = 'https://doanhnghiepmoi.vn/Ha-Tinh/';
      if (pageIndex > 1) {
        url = `https://doanhnghiepmoi.vn/Ha-Tinh/trang-${pageIndex}/`;
      }

      console.log(`\n--- Đang crawl trang ${pageIndex} => ${url} ---`);

      // Truy cập URL
      await page.goto(url, { waitUntil: 'networkidle2', timeout: 0 });
      // Lấy HTML
      const html = await page.content();
      const $ = cheerio.load(html);

      // Mảng tạm cho trang này
      let pageData = [];

      // Xử lý từng khối <li class="company-item">
      $('li.company-item').each((i, el) => {
        const nameElem = $(el).find('h3.company-name a');
        const name = nameElem.text().trim();
        const detailURL = nameElem.attr('href') || '';

        // <p> đầu tiên: "Mã số thuế: ... - Đại diện pháp luật: ..."
        const pFirst = $(el).find('p').first().text().trim();
        // Tách theo dấu "-" để lấy Mã số thuế và Chủ sở hữu
        let [taxText, daiDienText] = pFirst.split('-').map(s => s.trim());
        // taxText = "Mã số thuế: xxxxx"
        // daiDienText = "Đại diện pháp luật: Tên ..."
        let maSoThue = taxText.replace('Mã số thuế:', '').trim();
        let chuSoHuu = daiDienText.replace('Đại diện pháp luật:', '').trim();

        // <p> thứ hai: "Địa chỉ: ..."
        const pSecond = $(el).find('p').eq(1).text().trim();
        let diaChi = pSecond.replace('Địa chỉ:', '').trim();

        pageData.push({
          'Name': name,
          'URL': detailURL,
          'Mã số thuế': maSoThue,
          'Chủ sở hữu': chuSoHuu,
          'Địa chỉ': diaChi,
        });
      });

      console.log(`  -> Thu được ${pageData.length} công ty trên trang này.`);

      // Ghép dữ liệu trang này vào results
      results = results.concat(pageData);

      // 3) Lưu ngay vào file Excel sau mỗi trang
      //    - Tạo workbook mới & sheet
      const newWorkbook = XLSX.utils.book_new();
      const newWorksheet = XLSX.utils.json_to_sheet(results);
      XLSX.utils.book_append_sheet(newWorkbook, newWorksheet, 'HaTinh');
      XLSX.writeFile(newWorkbook, fileName);

      console.log(`  -> Đã ghi tạm dữ liệu (tổng ${results.length}) vào file [${fileName}].`);
    }

    // Đóng trình duyệt
    await browser.close();
    console.log(`\nHoàn tất. Tổng số dòng trong file Excel: ${results.length}.`);

  } catch (err) {
    console.error('Lỗi:', err);
  }
})();

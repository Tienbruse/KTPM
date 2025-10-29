const puppeteer = require('puppeteer');
const cheerio = require('cheerio');
const XLSX = require('xlsx');
const fs = require('fs');

(async () => {
  try {
    const browser = await puppeteer.launch({
      headless: false,
      defaultViewport: null
    });

    const listingPage = await browser.newPage();
    await listingPage.goto('https://b2b.fairs.vn/vi', { waitUntil: 'networkidle2', timeout: 0 });

    await listingPage.waitForSelector('#options');
    await listingPage.select('#options', '2');

    await listingPage.waitForSelector('#provinces');
    await listingPage.select('#provinces', '4575');

    const timKiemSelector = 'span.hidden.md\\:inline';
    await listingPage.waitForSelector(timKiemSelector);
    await listingPage.click(timKiemSelector);

    let allResults = [];

    for (let currentPage = 1; currentPage <= 5; currentPage++) {
      console.log(`\n--- ĐANG XỬ LÝ TRANG ${currentPage} ---`);

      await new Promise(r => setTimeout(r, 3000));

      const html = await listingPage.content();
      const $ = cheerio.load(html);

      let pageResults = [];
      $('div.rounded-lg.overflow-hidden.shadow-md a.h-full.block').each((i, el) => {
        const productName = $(el).find('h3.text-lg.font-semibold').text().trim();
        let productLink = $(el).attr('href') || '';
        let base = 'https://b2b.fairs.vn';
        let companyLink = productLink.replace(/\/product$/, '');
        pageResults.push({
          productName,
          productLink: base + productLink,
          companyLink: base + companyLink
        });
      });
      console.log(`  -> Trang ${currentPage} có ${pageResults.length} sản phẩm`);

      for (let item of pageResults) {
        console.log(`     -> Parse công ty: ${item.companyLink}`);

        const detailPage = await browser.newPage();
        await detailPage.goto(item.companyLink, { waitUntil: 'networkidle2', timeout: 0 });

        let detailHtml = await detailPage.content();
        let $detail = cheerio.load(detailHtml);

        let companyName = '';
        let website = '';
        let address = '';
        let email = '';
        let phone = '';
        let taxCode = '';
        let employees = '';
        let introduction = '';
        let images = [];

        $detail('table.text-left tr').each((idx, row) => {
          let label = $detail(row).find('th').text().trim();
          let value = $detail(row).find('td').text().trim() || '';
          if (label.includes('Tên công ty')) {
            companyName = value;
          } else if (label.includes('Website')) {
            website = value;
          } else if (label.includes('Địa chỉ')) {
            address = value;
          } else if (label.includes('Email')) {
            email = value;
          } else if (label.includes('Điện thoại')) {
            phone = value;
          } else if (label.includes('Mã số thuế')) {
            taxCode = value;
          } else if (label.includes('Số lượng nhân viên')) {
            employees = value;
          }
        });

        let introDiv;
        $detail('h2.my-5.pt-3.text-xl.font-bold').each((i, h2) => {
          let headingText = $detail(h2).text().trim();
          if (headingText.includes('Giới thiệu')) {
            introDiv = $detail(h2).next('div');
          }
        });
        if (introDiv && introDiv.length > 0) {
          introduction = introDiv.text().trim() || '';
        }

        let imagesArr = [];
        $detail('h2.my-5.pt-3.text-xl.font-bold').each((i, h2) => {
          let headingText = $detail(h2).text().trim();
          if (headingText.includes('Hình ảnh')) {
            let imgDiv = $detail(h2).next('div');
            if (imgDiv && imgDiv.length > 0) {
              let imgEls = imgDiv.find('img');
              imgEls.each((j, im) => {
                let src = $detail(im).attr('src');
                imagesArr.push(src || '');
              });
            }
          }
        });
        images = imagesArr;

        item.companyName = companyName;
        item.website = website;
        item.address = address;
        item.email = email;
        item.phone = phone;
        item.taxCode = taxCode;
        item.employees = employees;
        item.introduction = introduction;
        item.images = images;

        await detailPage.close(); 
      }

      allResults = allResults.concat(pageResults);

      if (currentPage < 5) {
        console.log(`  -> Trở về listing page, click 'Tiếp' để sang trang ${currentPage+1}`);

        const paginationSelector = 'nav[aria-label="Pagination"]';
        await listingPage.waitForSelector(paginationSelector);

        const anchors = await listingPage.$$(paginationSelector + ' a');
        let foundNext = false;
        for (const anchor of anchors) {
          let txtHandle = await anchor.getProperty('innerText');
          let txt = (await txtHandle.jsonValue()).trim();
          if (txt === 'Tiếp') {
            await anchor.click();
            foundNext = true;
            break;
          }
        }
        if (!foundNext) {
          console.log("    -> Không tìm thấy nút 'Tiếp', dừng sớm");
          break;
        }
      }
    }

    console.log(`\nTổng record: ${allResults.length}`);

    let wb = XLSX.utils.book_new();
    let ws = XLSX.utils.json_to_sheet(allResults);
    XLSX.utils.book_append_sheet(wb, ws, 'Sheet1');
    XLSX.writeFile(wb, 'b2b_fairs_products.xlsx');
    console.log(`Đã lưu ${allResults.length} dòng vào file Excel`);

    await browser.close();
  } catch (err) {
    console.error("Lỗi:", err);
  }
})();

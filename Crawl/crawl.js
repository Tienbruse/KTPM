const puppeteer = require('puppeteer');
const fs = require('fs');
const xlsx = require('xlsx');

const BASE_URL = "https://b2b.fairs.vn";
const TIMEOUT = 120000; 
const DELAY_BETWEEN_REQUESTS = 2000; 
const OUTPUT_EXCEL = "ThongTinDoanhNghiep.xlsx";

function initExcelIfNeeded() {
  if (!fs.existsSync(OUTPUT_EXCEL)) {
    const wb = xlsx.utils.book_new();
    const ws = xlsx.utils.json_to_sheet([]);
    xlsx.utils.book_append_sheet(wb, ws, "Companies");
    xlsx.writeFile(wb, OUTPUT_EXCEL);
    console.log(`Đã tạo file Excel mới: ${OUTPUT_EXCEL}`);
  } else {
    console.log(`Đã tồn tại file Excel: ${OUTPUT_EXCEL} (sẽ được ghi thêm)`);
  }
}

function appendRowToExcel(rowData) {
  const wb = xlsx.readFile(OUTPUT_EXCEL);
  const ws = wb.Sheets["Companies"];

  xlsx.utils.sheet_add_json(ws, [rowData], { origin: -1, skipHeader: true });

  xlsx.writeFile(wb, OUTPUT_EXCEL);
}
async function initBrowser() {
  const browser = await puppeteer.launch({ headless: true });
  const page = await browser.newPage();
  await page.setDefaultNavigationTimeout(TIMEOUT);
  return { browser, page };
}

function buildUrl(pageNumber = 1, provinceId = 4575, size = 20) {
  const params = new URLSearchParams({
    current: pageNumber.toString(),
    province_id: provinceId.toString(),
    size: size.toString()
  });
  return `${BASE_URL}/vi?${params.toString()}`;
}

function isValidCompanyLink(link) {
  const finalLink = link.startsWith('http') ? link : BASE_URL + link;
  const pattern = /^https?:\/\/b2b\.fairs\.vn\/vi\/company\/.+\.[0-9]+$/;
  return pattern.test(finalLink);
}

async function getCompanies(page) {
  return await page.evaluate(() => {
    const data = [];
    const anchors = document.querySelectorAll(".rounded-lg.overflow-hidden.shadow-md a");
    anchors.forEach(company => {
      const name = company.querySelector("h3")?.innerText.trim();
      const link = company.getAttribute("href") || "";
      data.push({ name, link });
    });
    return data;
  });
}

async function getCompanyInfo(page, company) {
  const finalLink = company.link.startsWith('http') ? company.link : BASE_URL + company.link;

  console.log(`\nĐang truy cập: ${finalLink}`);
  await page.goto(finalLink, {
    waitUntil: 'domcontentloaded',
    timeout: TIMEOUT,
  });

  const info = await page.evaluate(() => {
    let details = {};

    const table = document.querySelector("table.text-left tbody.grid");
    if (table) {
      table.querySelectorAll("tr").forEach(row => {
        const key = row.querySelector("th")?.innerText.trim();
        const value = row.querySelector("td div")?.innerText.trim();
        if (key && value) {
          details[key] = value;
        }
      });
    }

    details.introduction = (function () {
      const heading = Array.from(document.querySelectorAll('h2'))
        .find(h2 => h2.textContent.trim().toLowerCase() === 'giới thiệu');
      if (!heading) return '';
      const container = heading.closest('div');
      if (!container) return '';
      let text = container.innerText || '';
      text = text.replace(/^Giới thiệu\s*/i, '').trim();
      return text;
    })();

    details.awards = (function () {
      const awardHeadings = Array.from(document.querySelectorAll('h2'))
        .filter(el => /giải thưởng|chứng chỉ|chứng nhận/i.test(el.textContent));
      const awardsData = awardHeadings.map(heading => {
        const container = heading.closest('div');
        return container ? container.innerText.trim() : '';
      });
      return awardsData.join('\n-------------------\n');
    })();

    details.images = (function () {
      const heading = Array.from(document.querySelectorAll('h2'))
        .find(h2 => h2.textContent.trim().toLowerCase() === 'hình ảnh');
      if (!heading) return [];
      const container = heading.closest('div');
      if (!container) return [];
      const imgs = container.querySelectorAll('img');
      return Array.from(imgs).map(img => img.src);
    })();

    return details;
  });

  return {
    Name: company.name,
    URL: finalLink,
    ...info,
  };
}

(async () => {
  initExcelIfNeeded();

  const { browser, page } = await initBrowser();

  try {
    for (let iPage = 500; iPage <= 600; iPage++) {
      const startUrl = buildUrl(iPage, 4575, 20);
      console.log(`\n==============`);
      console.log(`Trang: ${iPage}`);
      console.log(`URL: ${startUrl}`);
      console.log(`==============`);

      try {
        await page.goto(startUrl, { waitUntil: 'networkidle2', timeout: TIMEOUT });
      } catch (err) {
        console.error(`Lỗi khi mở trang ${startUrl}: ${err.message}`);
        continue;
      }

      let companies = await getCompanies(page);

      companies = companies.filter(c => isValidCompanyLink(c.link));
      console.log(`Tìm thấy ${companies.length} công ty hợp lệ`);

      for (let c of companies) {
        try {
          const companyData = await getCompanyInfo(page, c);
          appendRowToExcel(companyData);

          await new Promise(res => setTimeout(res, DELAY_BETWEEN_REQUESTS));

        } catch (err) {
          console.error(`Lỗi khi lấy dữ liệu từ ${c.link}: ${err.message}`);
        }
      }
    }
  } catch (err) {
    console.error(`Có lỗi xảy ra: ${err.message}`);
  } finally {
    await browser.close();
  }
})();

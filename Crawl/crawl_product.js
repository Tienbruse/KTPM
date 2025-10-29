const puppeteer = require('puppeteer');
const fs = require('fs');
const xlsx = require('xlsx');

const BASE_URL = "https://b2b.fairs.vn";
const TIMEOUT = 120000; 
const DELAY_BETWEEN_REQUESTS = 2000; 
const OUTPUT_EXCEL = "ThongTinSanPham.xlsx";

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

/**
 * Hàm xây dựng URL phân trang (nếu trang vẫn chấp nhận các query này).
 * Chúng ta vẫn để search_type = product, province_id = 4575,
 * nhưng quan trọng là trang hiện tại vẫn cần thao tác client-side để filter theo "Sản phẩm".
 */
function buildUrl(pageNumber = 1, search_type = "product", provinceId = 4575) {
  const params = new URLSearchParams({
    current: pageNumber.toString(),
    search_type: search_type,
    province_id: provinceId.toString(),
  });
  return `${BASE_URL}/vi?${params.toString()}`;
}

/**
 * Kiểm tra link có hợp lệ là /vi/company/... hay không
 */
function isValidCompanyLink(link) {
  const finalLink = link.startsWith('http') ? link : BASE_URL + link;
  const pattern = /^https?:\/\/b2b\.fairs\.vn\/vi\/company\/.+\.[0-9]+$/;
  return pattern.test(finalLink);
}

/**
 * Hàm lấy danh sách "công ty" (thực tế trang hiển thị block, 
 * nhưng do code gốc dùng h3 -> hiển thị theo company).
 * Ở đây ta vẫn giữ tên hàm, nhưng nó sẽ quét các thẻ 
 * .rounded-lg.overflow-hidden.shadow-md a => ra link & name 
 */
async function getCompanies(page) {
  // Lưu ý: Nếu trang hiển thị "Sản phẩm" trong <h5>, 
  // thì logic dưới sẽ vẫn tìm <h3>. 
  // Kiểm tra thực tế HTML để sửa lại cho đúng (ví dụ h5 thay cho h3).
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

/**
 * Hàm lấy thông tin của công ty + sản phẩm của công ty 
 * (finalLink + "/product"), sau đó đi vào từng trang chi tiết sản phẩm.
 */
async function getCompanyInfo(page, company) {
  // 1. Lấy thông tin công ty như trước
  const finalLink = company.link.startsWith('http') ? company.link : BASE_URL + company.link;
  console.log(`\nĐang truy cập trang công ty: ${finalLink}`);

  await page.goto(finalLink, {
    waitUntil: 'domcontentloaded',
    timeout: TIMEOUT,
  });

  // Lấy info công ty
  const info = await page.evaluate(() => {
    let details = {};

    // Lấy thông tin từ bảng "table.text-left tbody.grid"
    const table = document.querySelector("table.text-left tbody.grid");
    if (table) {
      table.querySelectorAll("tr").forEach((row) => {
        const key = row.querySelector("th")?.innerText.trim();
        const value = row.querySelector("td div")?.innerText.trim();
        if (key && value) {
          details[key] = value;
        }
      });
    }

    // Giới thiệu
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

    // Giải thưởng / Chứng chỉ
    details.awards = (function () {
      const awardHeadings = Array.from(document.querySelectorAll('h2'))
        .filter(el => /giải thưởng|chứng chỉ|chứng nhận/i.test(el.textContent));
      const awardsData = awardHeadings.map(heading => {
        const container = heading.closest('div');
        return container ? container.innerText.trim() : '';
      });
      return awardsData.join('\n-------------------\n');
    })();

    // Hình ảnh liên quan đến công ty
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

  // 2. Lấy danh sách sản phẩm của công ty (finalLink + "/product")
  const productPageUrl = finalLink + '/product';
  console.log(`Đang truy cập trang sản phẩm của công ty: ${productPageUrl}`);

  // Điều hướng sang trang /product
  try {
    await page.goto(productPageUrl, {
      waitUntil: 'domcontentloaded',
      timeout: TIMEOUT,
    });
  } catch (err) {
    console.error(`Lỗi khi mở trang sản phẩm: ${productPageUrl} - ${err.message}`);
    // Vẫn trả về thông tin công ty, có thể chưa có sản phẩm
    return {
      Name: company.name,
      URL: finalLink,
      ...info
    };
  }

  // 3. Lấy danh sách link & tên sản phẩm
  const products = await page.evaluate(() => {
    // Mỗi sản phẩm thường nằm trong thẻ div .shadow-md.rounded.overflow-hidden
    const items = document.querySelectorAll(".shadow-md.rounded.overflow-hidden");
    const results = [];
    items.forEach((item) => {
      const anchor = item.querySelector("a");
      const titleEl = item.querySelector("h5");
      const link = anchor ? anchor.getAttribute('href') : '';
      const name = titleEl ? titleEl.innerText.trim() : '';
      if (link && name) {
        results.push({ name, link });
      }
    });
    return results;
  });

  console.log(`Tìm thấy ${products.length} sản phẩm`);

  // 4. Lấy thông tin chi tiết từ từng sản phẩm
  const productDetails = [];
  for (let product of products) {
    const detailUrl = product.link.startsWith('http') ? product.link : (BASE_URL + product.link);

    console.log(`   => Đang truy cập sản phẩm: ${detailUrl}`);
    try {
      await page.goto(detailUrl, {
        waitUntil: 'domcontentloaded',
        timeout: TIMEOUT,
      });
    } catch (err) {
      console.error(`Lỗi khi mở trang chi tiết sản phẩm ${detailUrl}: ${err.message}`);
      continue;
    }

    const prodInfo = await page.evaluate(() => {
      let pInfo = {};

      // Tên sản phẩm
      const nameEl = document.querySelector("h2.my-1.font-bold.text-2xl");
      pInfo.productName = nameEl ? nameEl.innerText.trim() : '';

      // Giá sản phẩm
      const priceBlock = Array.from(document.querySelectorAll("div.my-1"))
        .find(el => el.innerText.includes("Giá:"));
      if (priceBlock) {
        const linkEl = priceBlock.querySelector("span a");
        pInfo.price = linkEl ? linkEl.innerText.trim() : priceBlock.innerText.replace("Giá:", "").trim();
      } else {
        pInfo.price = '';
      }

      // Mô tả sản phẩm
      let description = '';
      const descHeading = Array.from(document.querySelectorAll('h3'))
        .find(h3 => h3.innerText.trim().toLowerCase() === 'mô tả');
      if (descHeading) {
        const descContainer = descHeading.closest('div');
        if (descContainer) {
          const pEls = descContainer.querySelectorAll('p');
          if (pEls.length > 0) {
            description = Array.from(pEls).map(p => p.innerText.trim()).join('\n');
          }
        }
      }
      pInfo.description = description;

      // Số lượng tối thiểu
      const minOrderBlock = Array.from(document.querySelectorAll("div.my-1"))
        .find(el => el.innerText.includes("Số lượng đặt mua tối thiểu:"));
      pInfo.minOrder = minOrderBlock 
        ? minOrderBlock.innerText.replace("Số lượng đặt mua tối thiểu:", "").trim() 
        : '';

      // Khả năng cung ứng
      const supplyBlock = Array.from(document.querySelectorAll("div.my-1"))
        .find(el => el.innerText.includes("Khả năng cung ứng:"));
      pInfo.supplyAbility = supplyBlock 
        ? supplyBlock.innerText.replace("Khả năng cung ứng:", "").trim() 
        : '';

      // Hình ảnh sản phẩm
      const imgEls = document.querySelectorAll("img");
      pInfo.images = [];
      imgEls.forEach(img => {
        const src = img.getAttribute('src') || '';
        if (src.includes('https://a.fairs.vn/image/')) {
          pInfo.images.push(src);
        }
      });

      return pInfo;
    });

    const productRow = {
      Name: company.name,              // Tên công ty
      CompanyURL: finalLink,           // Link công ty
      ProductName: prodInfo.productName,
      ProductURL: detailUrl,
      Price: prodInfo.price,
      MinOrder: prodInfo.minOrder,
      SupplyAbility: prodInfo.supplyAbility,
      ProductDescription: prodInfo.description,
      ProductImages: (prodInfo.images || []).join('\n'),
    };

    productDetails.push(productRow);
    // Hoặc ghi ngay vào Excel tại đây: appendRowToExcel(productRow);
  }

  return {
    Name: company.name,
    URL: finalLink,
    ...info,
    products: productDetails
  };
}

(async () => {
  initExcelIfNeeded();

  const { browser, page } = await initBrowser();

  try {
    for (let iPage = 1; iPage <= 695; iPage++) {
      // Xây dựng URL phân trang
      const startUrl = buildUrl(iPage, "product", 4575);
      console.log(`\n==============`);
      console.log(`Trang: ${iPage}`);
      console.log(`URL: ${startUrl}`);
      console.log(`==============`);

      try {
        // Đi đến trang phân trang
        await page.goto(startUrl, { waitUntil: 'networkidle2', timeout: TIMEOUT });

        // 1. Mô phỏng CHỌN "Sản phẩm" trong dropdown nếu trang yêu cầu
        await page.waitForSelector('#options');
        // value="2" => Sản phẩm, theo HTML cho sẵn
        await page.select('#options', '2');

        // Nếu trang có nút "Tìm kiếm" hoặc "Lọc", bạn click:
        // await page.click('#searchBtn'); // ví dụ
        // await page.waitForNavigation({ waitUntil: 'networkidle2' });

        // 2. Chờ danh sách hiển thị lại
        //   Kiểm tra selector hiển thị link => .rounded-lg.overflow-hidden.shadow-md a
        await page.waitForSelector('.rounded-lg.overflow-hidden.shadow-md a', {
          timeout: TIMEOUT
        });

      } catch (err) {
        console.error(`Lỗi khi mở trang ${startUrl}: ${err.message}`);
        continue;
      }

      // 3. Lấy "companies" (thực chất là block hiển thị - code gốc)
      let companies = await getCompanies(page);

      companies = companies.filter(c => isValidCompanyLink(c.link));
      console.log(`Tìm thấy ${companies.length} công ty/sản phẩm hợp lệ`);

      // 4. Duyệt từng đối tượng để lấy thông tin chi tiết
      for (let c of companies) {
        try {
          const companyData = await getCompanyInfo(page, c);
          // Ghi từng sản phẩm vào Excel
          for (const prod of companyData.products) {
            appendRowToExcel(prod);
          }

          // Tạo độ trễ giữa các lần request
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

const XLSX = require('xlsx');
const fs = require('fs');

const inputFile = 'thongtindoanhnghiep.xlsx';

const outputFile = 'b2bbusiness.xlsx';

try {
  if (!fs.existsSync(inputFile)) {
    console.log(`Không tìm thấy file [${inputFile}]. Dừng xử lý.`);
    process.exit(1);
  }
  const workbook = XLSX.readFile(inputFile);

  const sheetName = workbook.SheetNames[0];
  const worksheet = workbook.Sheets[sheetName];

  const jsonData = XLSX.utils.sheet_to_json(worksheet, { defval: '' });

  console.log('Số dòng ban đầu:', jsonData.length);

  let seen = new Set();
  let deduplicated = [];

  for (let row of jsonData) {
    const signature = JSON.stringify(row);

    if (!seen.has(signature)) {
      seen.add(signature);
      deduplicated.push(row);
    }
  }

  console.log('Số dòng sau khi xóa trùng lặp:', deduplicated.length);

  const newWorkbook = XLSX.utils.book_new();
  const newWorksheet = XLSX.utils.json_to_sheet(deduplicated);
  XLSX.utils.book_append_sheet(newWorkbook, newWorksheet, 'Sheet1');
  XLSX.writeFile(newWorkbook, outputFile);

  console.log(`Đã ghi file không trùng lặp ra: ${outputFile}`);
} catch (err) {
  console.error('Lỗi:', err);
}

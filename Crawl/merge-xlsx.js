const fs = require('fs');
const XLSX = require('xlsx');
const path = require('path');

// Thư mục chứa các file excel cần gộp
const dirPath = '/Users/Tienbruse/tmdt/Chatbot-test/Crawl/hatinhplaza';

// File kết quả sau khi gộp
const outputFileName = 'merged_hatiplaza.xlsx';

let mergedData = [];

// Đọc tất cả file excel trong thư mục
fs.readdirSync(dirPath).forEach(file => {
  if (file.endsWith('.xlsx') && file !== outputFileName) {
    console.log(`Đang đọc file: ${file}`);
    const workbook = XLSX.readFile(path.join(dirPath, file));
    const sheetName = workbook.SheetNames[0];
    const worksheet = workbook.Sheets[sheetName];
    const data = XLSX.utils.sheet_to_json(worksheet, { defval: '' });
    mergedData = mergedData.concat(data);
  }
});

// Ghi dữ liệu gộp vào file mới
const newWorkbook = XLSX.utils.book_new();
const newWorksheet = XLSX.utils.json_to_sheet(mergedData);
XLSX.utils.book_append_sheet(newWorkbook, newWorksheet, 'MergedData');
XLSX.writeFile(newWorkbook, outputFileName);

console.log(`Hoàn tất gộp dữ liệu! Tổng cộng ${mergedData.length} dòng dữ liệu vào file ${outputFileName}.`);

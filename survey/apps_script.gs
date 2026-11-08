// Code.gs: web app of the questionnaire. index.html = survey/phishing_survey.html.
// Replace SHEET_ID with the ID of your Google Sheet (the part of its URL between /d/ and /edit).
var SHEET_ID = "PUT_SHEET_ID_HERE";

function doGet() {
  return HtmlService.createHtmlOutputFromFile("index")
    .setTitle("Опрос: распознавание фишинговых писем")
    .addMetaTag("viewport", "width=device-width, initial-scale=1")
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}
function save_(text) {
  var sheet = SpreadsheetApp.openById(SHEET_ID).getSheets()[0];
  String(text || "").split("\n").forEach(function (line) {
    line = line.trim();
    if (!line) return;
    try { JSON.parse(line); } catch (err) { return; }   // keep only valid JSON
    sheet.appendRow([line]);
  });
}
function saveAnswers(text) { save_(text); return "ok"; }   // called by google.script.run
function doPost(e) { save_((e.postData && e.postData.contents) || ""); return ContentService.createTextOutput("ok"); }

import os
import sys

GOOGLE_APPS_SCRIPT_CODE = """/**
 * Google Apps Script Webhook for AI Video Automation
 * Paste this into: Extensions -> Apps Script in your Google Sheet!
 */
function doPost(e) {
  try {
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
    var data = JSON.parse(e.postData.contents);
    
    // Auto-create headers if first row is empty
    if (sheet.getLastRow() === 0) {
      sheet.appendRow([
        "Timestamp (UTC)",
        "Job ID",
        "Category",
        "Title / Headline",
        "Script Hook",
        "Duration",
        "Word Count",
        "AI Engine / Key",
        "Voice Engine",
        "Free Storage (Telegram)",
        "YouTube Shorts Link",
        "Instagram Link",
        "Facebook Link",
        "Status",
        "Execution Log",
        "Source URL"
      ]);
      sheet.getRange(1, 1, 1, 16).setFontWeight("bold").setBackground("#0f172a").setFontColor("#38bdf8");
      sheet.setFrozenRows(1);
    }
    
    sheet.appendRow([
      data.timestamp || new Date().toISOString(),
      data.job_id || "-",
      data.category || "Cybersecurity",
      data.title || "",
      data.hook || "",
      data.duration || "-",
      data.word_count || "-",
      data.key_used || "AI Generator",
      data.voice || "Edge-TTS",
      data.storage_url || "",
      data.youtube_url || "",
      data.instagram_url || "",
      data.facebook_url || "",
      data.status || "completed",
      data.execution_log || "",
      data.source_url || ""
    ]);
    
    return ContentService.createTextOutput(JSON.stringify({result: "success"})).setMimeType(ContentService.MimeType.JSON);
  } catch (error) {
    return ContentService.createTextOutput(JSON.stringify({result: "error", message: error.toString()})).setMimeType(ContentService.MimeType.JSON);
  }
}
"""

def main():
    print("======================================================================")
    print("📊 GOOGLE SHEETS AUTOMATION SETUP HELPER")
    print("======================================================================")
    print("\nYou have TWO convenient ways to connect your Google Spreadsheet:\n")
    print("METHOD 1: Instant Webhook (Easiest - 1 minute setup, NO Google Cloud required!)")
    print("----------------------------------------------------------------------")
    print("1. Create a new Google Sheet at https://sheets.new")
    print("2. In the top menu, click: Extensions -> Apps Script")
    print("3. Delete any code there, and paste the following script:\n")
    print(GOOGLE_APPS_SCRIPT_CODE)
    print("4. Click 'Deploy' (top right) -> 'New Deployment'")
    print("5. Select type: 'Web app'")
    print("6. Set 'Execute as': Me, and 'Who has access': Anyone")
    print("7. Click 'Deploy', authorize it, and copy the Web App URL.")
    print("8. Paste that URL into your .env file as:")
    print("   GOOGLE_SHEET_WEBHOOK_URL=https://script.google.com/macros/s/...\n")
    
    print("METHOD 2: Google Cloud Service Account (gspread)")
    print("----------------------------------------------------------------------")
    print("1. Go to https://console.cloud.google.com and create a project.")
    print("2. Enable the 'Google Sheets API' and 'Google Drive API'.")
    print("3. Create a Service Account, generate a JSON Key, and save it as 'google_sheets_creds.json'.")
    print("4. Share your Google Sheet with the service account client email (Editor access).")
    print("5. Set GOOGLE_SHEET_NAME in your .env to your sheet title.\n")

    print("======================================================================")
    print("✅ Ready-to-copy Google Sheet Template Link:")
    print("https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/copy")
    print("======================================================================")

if __name__ == "__main__":
    main()


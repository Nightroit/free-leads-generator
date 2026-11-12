document.getElementById("download").addEventListener("click", async () => {
  const status = document.getElementById("status");
  status.textContent = "Scanning page...";

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

  chrome.scripting.executeScript({
    target: { tabId: tab.id },
    func: collectPdfLinks
  }, (results) => {
    const links = results?.[0]?.result || [];
    if (!links.length) {
      status.textContent = "No PDF links found.";
      return;
    }
    status.textContent = `Found ${links.length} PDFs. Downloading...`;
    chrome.runtime.sendMessage({ action: "download", urls: links });
  });
});

function collectPdfLinks() {
  const links = Array.from(document.querySelectorAll("a[href]"));
  const pdfs = [];
  const seen = new Set();

  for (const a of links) {
    const href = a.href;
    const text = (a.innerText || "").toLowerCase();
    if (!href || seen.has(href)) continue;

    if (
      href.toLowerCase().endsWith(".pdf") ||
      href.toLowerCase().includes(".pdf?") ||
      text.includes("pdf") ||
      text.includes("[pdf]")
    ) {
      seen.add(href);
      pdfs.push(href);
    }
  }
  return pdfs;
}

chrome.runtime.onMessage.addListener((msg) => {
  if (msg.action === "download" && Array.isArray(msg.urls)) {
    msg.urls.forEach((url, i) => {
      setTimeout(() => {
        chrome.downloads.download({
          url: url,
          saveAs: false
        });
      }, i * 1500); // 1.5s delay between downloads
    });
  }
});


// background.js - 后台脚本
chrome.runtime.onInstalled.addListener(() => {
    console.log('论文库检查器已安装');
});

// 处理插件图标点击
chrome.action.onClicked.addListener((tab) => {
    if (tab.url.includes('scholar.google.com')) {
        chrome.scripting.executeScript({
            target: { tabId: tab.id },
            function: () => {
                if (window.paperChecker) {
                    window.paperChecker.checkPapers();
                }
            }
        });
    }
});

// 监听标签页更新
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (changeInfo.status === 'complete' && tab.url && tab.url.includes('scholar.google.com')) {
        // 谷歌学术页面加载完成，准备检查论文
        setTimeout(() => {
            chrome.scripting.executeScript({
                target: { tabId: tabId },
                function: () => {
                    if (window.paperChecker) {
                        window.paperChecker.checkPapers();
                    }
                }
            });
        }, 2000);
    }
});

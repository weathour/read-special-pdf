
// popup.js - 弹出窗口脚本
document.addEventListener('DOMContentLoaded', async () => {
    const apiStatusElement = document.getElementById('apiStatus');
    const statusTextElement = document.getElementById('statusText');
    const statusIconElement = document.getElementById('statusIcon');
    const enableToggle = document.getElementById('enableToggle');
    const refreshBtn = document.getElementById('refreshBtn');
    const clearBtn = document.getElementById('clearBtn');
    const totalPapersElement = document.getElementById('totalPapers');
    const foundPapersElement = document.getElementById('foundPapers');
    const dbTotalElement = document.getElementById('dbTotal');

    const API_BASE_URL = 'http://localhost:5002/api';

    // 检查API状态
    async function checkApiStatus() {
        try {
            const response = await fetch(`${API_BASE_URL}/health`);
            if (response.ok) {
                apiStatusElement.className = 'status online';
                statusTextElement.textContent = 'API 在线';
                statusIconElement.textContent = '✅';
                return true;
            } else {
                throw new Error('API响应错误');
            }
        } catch (error) {
            apiStatusElement.className = 'status offline';
            statusTextElement.textContent = 'API 离线';
            statusIconElement.textContent = '❌';
            return false;
        }
    }

    // 获取数据库统计信息
    async function getDbStats() {
        try {
            const response = await fetch(`${API_BASE_URL}/stats`);
            if (response.ok) {
                const stats = await response.json();
                dbTotalElement.textContent = stats.total_papers;
            }
        } catch (error) {
            console.error('获取数据库统计失败:', error);
        }
    }

    // 获取当前页面统计信息
    async function getPageStats() {
        try {
            const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
            
            if (tab.url.includes('scholar.google.com')) {
                const results = await chrome.scripting.executeScript({
                    target: { tabId: tab.id },
                    function: () => {
                        const totalPapers = document.querySelectorAll('.gs_ri').length;
                        const foundPapers = document.querySelectorAll('.paper-in-library').length;
                        return { totalPapers, foundPapers };
                    }
                });

                if (results && results[0]) {
                    const { totalPapers, foundPapers } = results[0].result;
                    totalPapersElement.textContent = totalPapers;
                    foundPapersElement.textContent = foundPapers;
                }
            } else {
                totalPapersElement.textContent = '非谷歌学术页面';
                foundPapersElement.textContent = '-';
            }
        } catch (error) {
            console.error('获取页面统计失败:', error);
        }
    }

    // 切换检查器状态
    enableToggle.addEventListener('change', async () => {
        const enabled = enableToggle.checked;
        
        try {
            const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
            
            await chrome.tabs.sendMessage(tab.id, {
                action: 'toggleChecker',
                enabled: enabled
            });
            
            // 更新页面统计
            setTimeout(getPageStats, 1000);
        } catch (error) {
            console.error('切换检查器状态失败:', error);
        }
    });

    // 重新检查按钮
    refreshBtn.addEventListener('click', async () => {
        refreshBtn.textContent = '🔄 检查中...';
        refreshBtn.disabled = true;
        
        try {
            const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
            
            // 刷新页面检查
            await chrome.scripting.executeScript({
                target: { tabId: tab.id },
                function: () => {
                    if (window.paperChecker) {
                        window.paperChecker.clearMarkers();
                        window.paperChecker.checkedPapers.clear();
                        window.paperChecker.cache.clear();
                        window.paperChecker.checkPapers();
                    }
                }
            });
            
            setTimeout(getPageStats, 2000);
        } catch (error) {
            console.error('重新检查失败:', error);
        }
        
        refreshBtn.textContent = '🔄 重新检查';
        refreshBtn.disabled = false;
    });

    // 清除标记按钮
    clearBtn.addEventListener('click', async () => {
        try {
            const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
            
            await chrome.scripting.executeScript({
                target: { tabId: tab.id },
                function: () => {
                    if (window.paperChecker) {
                        window.paperChecker.clearMarkers();
                    }
                }
            });
            
            getPageStats();
        } catch (error) {
            console.error('清除标记失败:', error);
        }
    });

    // 初始化
    await checkApiStatus();
    await getDbStats();
    await getPageStats();
});

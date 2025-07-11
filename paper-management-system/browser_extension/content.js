
// content.js - 在谷歌学术页面运行的脚本
class PaperChecker {
    constructor() {
        this.API_BASE_URL = 'http://localhost:5002/api';
        this.checkedPapers = new Set();
        this.cache = new Map();
        this.isEnabled = true;
        this.init();
    }

    async init() {
        console.log('📚 论文库检查器启动');
        
        // 检查API是否可用
        const apiAvailable = await this.checkApiHealth();
        if (!apiAvailable) {
            console.error('❌ API不可用');
            this.showNotification('论文库检查器API连接失败', 'error');
            return;
        }

        // 检查论文
        await this.checkPapers();
        
        // 监听页面变化
        this.observePageChanges();
        
        // 监听来自popup的消息
        chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
            if (request.action === 'toggleChecker') {
                this.isEnabled = request.enabled;
                if (this.isEnabled) {
                    this.checkPapers();
                } else {
                    this.clearMarkers();
                }
                sendResponse({success: true});
            }
        });
    }

    async checkApiHealth() {
        try {
            const response = await fetch(`${this.API_BASE_URL}/health`);
            return response.ok;
        } catch (error) {
            console.error('API健康检查失败:', error);
            return false;
        }
    }

    observePageChanges() {
        const observer = new MutationObserver((mutations) => {
            let shouldCheck = false;
            mutations.forEach(mutation => {
                if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                    shouldCheck = true;
                }
            });
            
            if (shouldCheck && this.isEnabled) {
                setTimeout(() => this.checkPapers(), 1000);
            }
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }

    extractPaperInfo(paperElement) {
        try {
            // 提取标题
            const titleElement = paperElement.querySelector('h3 a, h3');
            if (!titleElement) return null;
            
            const title = titleElement.textContent.trim();
            
            // 提取作者和年份信息
            const authorsElement = paperElement.querySelector('.gs_a');
            let authors = [];
            let year = '';
            
            if (authorsElement) {
                const authorsText = authorsElement.textContent;
                
                // 提取作者（通常在第一个破折号之前）
                const authorsPart = authorsText.split('-')[0];
                if (authorsPart) {
                    authors = authorsPart.split(',').map(a => a.trim()).filter(a => a);
                }
                
                // 提取年份
                const yearMatch = authorsText.match(/(\d{4})/);
                if (yearMatch) {
                    year = yearMatch[1];
                }
            }

            // 提取DOI（如果存在）
            let doi = '';
            const links = paperElement.querySelectorAll('a');
            for (const link of links) {
                if (link.href && link.href.includes('doi.org')) {
                    doi = link.href.split('doi.org/')[1];
                    break;
                }
            }

            return {
                title,
                authors,
                year,
                doi,
                element: paperElement
            };
        } catch (error) {
            console.error('提取论文信息失败:', error);
            return null;
        }
    }

    async checkPapers() {
        if (!this.isEnabled) return;

        // 获取所有论文元素
        const paperElements = document.querySelectorAll('.gs_ri');
        console.log(`🔍 找到 ${paperElements.length} 篇论文`);

        const papersToCheck = [];
        
        for (const paperElement of paperElements) {
            const paperInfo = this.extractPaperInfo(paperElement);
            
            if (!paperInfo || this.checkedPapers.has(paperInfo.title)) {
                continue;
            }

            // 检查缓存
            if (this.cache.has(paperInfo.title)) {
                const cachedResult = this.cache.get(paperInfo.title);
                if (cachedResult.found) {
                    this.markPaperAsInLibrary(paperInfo.element, cachedResult.matches[0]);
                }
                continue;
            }

            papersToCheck.push(paperInfo);
        }

        // 批量检查论文
        if (papersToCheck.length > 0) {
            await this.batchCheckPapers(papersToCheck);
        }
    }

    async batchCheckPapers(papers) {
        try {
            const requestData = {
                papers: papers.map(p => ({
                    title: p.title,
                    authors: p.authors,
                    year: p.year,
                    doi: p.doi
                }))
            };

            const response = await fetch(`${this.API_BASE_URL}/batch-check`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestData)
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const result = await response.json();
            
            // 处理结果
            result.results.forEach((paperResult, index) => {
                const paperInfo = papers[index];
                
                // 缓存结果
                this.cache.set(paperInfo.title, paperResult);
                this.checkedPapers.add(paperInfo.title);
                
                // 标记找到的论文
                if (paperResult.found && paperResult.matches.length > 0) {
                    this.markPaperAsInLibrary(paperInfo.element, paperResult.matches[0]);
                }
            });

            console.log(`✅ 批量检查完成: ${result.total_found}/${result.total_checked} 篇已收录`);
            
        } catch (error) {
            console.error('批量检查论文失败:', error);
            
            // 降级为单个检查
            for (const paperInfo of papers) {
                await this.checkSinglePaper(paperInfo);
            }
        }
    }

    async checkSinglePaper(paperInfo) {
        try {
            const response = await fetch(`${this.API_BASE_URL}/check-paper`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    title: paperInfo.title,
                    authors: paperInfo.authors,
                    year: paperInfo.year,
                    doi: paperInfo.doi
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const result = await response.json();
            
            // 缓存结果
            this.cache.set(paperInfo.title, result);
            this.checkedPapers.add(paperInfo.title);
            
            if (result.found && result.matches.length > 0) {
                this.markPaperAsInLibrary(paperInfo.element, result.matches[0]);
            }
            
        } catch (error) {
            console.error('检查单篇论文失败:', error);
        }
    }

    markPaperAsInLibrary(paperElement, match) {
        // 检查是否已经标记
        if (paperElement.querySelector('.paper-checker-badge')) {
            return;
        }

        // 创建标记
        const badge = document.createElement('div');
        badge.className = 'paper-checker-badge';
        badge.innerHTML = `
            <span class="badge-text">
                📚 已收录 ${Math.round(match.confidence * 100)}%
            </span>
        `;

        // 添加到标题
        const titleElement = paperElement.querySelector('h3');
        if (titleElement) {
            titleElement.appendChild(badge);
        }

        // 添加边框高亮
        paperElement.classList.add('paper-in-library');
        
        // 添加悬停信息
        badge.title = `匹配方法: ${match.match_method}\n置信度: ${Math.round(match.confidence * 100)}%\n文件: ${match.file_name}`;
    }

    clearMarkers() {
        // 移除所有标记
        document.querySelectorAll('.paper-checker-badge').forEach(badge => {
            badge.remove();
        });
        
        document.querySelectorAll('.paper-in-library').forEach(element => {
            element.classList.remove('paper-in-library');
        });
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `paper-checker-notification ${type}`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 5000);
    }
}

// 启动检查器
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        new PaperChecker();
    });
} else {
    new PaperChecker();
}

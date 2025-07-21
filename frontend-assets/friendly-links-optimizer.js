/**
 * Friendly Links Avatar Loading Optimizer
 * 优化友链头像加载体验
 * 
 * 使用方法：
 * 1. 引入此文件到你的博客
 * 2. 在页面加载后调用 FriendlyLinksOptimizer.init()
 */

class FriendlyLinksOptimizer {
    constructor(options = {}) {
        this.options = {
            // 默认配置
            selector: '.friend-avatar, .reader-avatar', // 头像选择器
            loadingClass: 'avatar-loading',
            loadedClass: 'avatar-loaded',
            errorClass: 'avatar-error',
            batchSize: 3, // 批次加载大小
            batchDelay: 200, // 批次延迟(ms)
            retryTimes: 2, // 重试次数
            timeout: 8000, // 超时时间(ms)
            lazyLoad: true, // 是否启用懒加载
            ...options
        };
        
        this.loadedCache = new Map(); // 已加载的头像缓存
        this.imageObserver = null; // 懒加载观察器
    }
    
    /**
     * 初始化优化器
     */
    init() {
        console.log('🚀 Friendly Links Optimizer initialized');
        
        // 添加CSS样式
        this.injectStyles();
        
        // 获取所有头像元素
        const avatars = document.querySelectorAll(this.options.selector);
        
        if (avatars.length === 0) {
            console.warn('No avatar elements found');
            return;
        }
        
        // 预处理头像元素
        this.preprocessAvatars(avatars);
        
        // 根据配置选择加载策略
        if (this.options.lazyLoad) {
            this.initLazyLoading(avatars);
        } else {
            this.initBatchLoading(avatars);
        }
    }
    
    /**
     * 注入优化样式
     */
    injectStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .avatar-loading {
                opacity: 0.6;
                background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
                background-size: 200% 100%;
                animation: avatar-shimmer 1.5s infinite;
                transition: all 0.3s ease;
            }
            
            .avatar-loaded {
                opacity: 1;
                animation: avatar-fade-in 0.5s ease;
            }
            
            .avatar-error {
                opacity: 0.7;
                filter: grayscale(50%);
            }
            
            @keyframes avatar-shimmer {
                0% { background-position: -200% 0; }
                100% { background-position: 200% 0; }
            }
            
            @keyframes avatar-fade-in {
                from { opacity: 0.6; transform: scale(0.95); }
                to { opacity: 1; transform: scale(1); }
            }
            
            /* 读者墙特定样式 */
            .reader-wall .avatar-loading {
                border-radius: 50%;
            }
            
            /* 友链列表特定样式 */
            .friend-links .avatar-loading {
                border-radius: 8px;
            }
        `;
        document.head.appendChild(style);
    }
    
    /**
     * 预处理头像元素
     */
    preprocessAvatars(avatars) {
        avatars.forEach((img, index) => {
            // 保存原始URL
            const originalSrc = img.src || img.dataset.src;
            img.dataset.originalSrc = originalSrc;
            img.dataset.index = index;
            
            // 设置加载状态
            img.classList.add(this.options.loadingClass);
            
            // 设置占位符
            this.setPlaceholder(img);
            
            // 添加错误处理
            img.addEventListener('error', () => this.handleImageError(img));
        });
    }
    
    /**
     * 设置占位符
     */
    setPlaceholder(img) {
        // 从JSON数据中获取占位符（如果有的话）
        const friendData = this.getFriendDataFromElement(img);
        
        if (friendData && friendData.avatar_placeholder) {
            img.src = friendData.avatar_placeholder;
        } else {
            // 生成默认占位符
            const title = img.alt || img.dataset.title || 'User';
            img.src = this.generatePlaceholder(title);
        }
    }
    
    /**
     * 生成占位符SVG
     */
    generatePlaceholder(title) {
        const initial = title.charAt(0).toUpperCase();
        const colors = ['#6366f1', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#3b82f6'];
        const color = colors[title.length % colors.length];
        
        const svg = `
            <svg width="64" height="64" xmlns="http://www.w3.org/2000/svg">
                <rect width="64" height="64" fill="${color}"/>
                <text x="32" y="40" text-anchor="middle" font-size="24" font-weight="bold" fill="white">
                    ${initial}
                </text>
            </svg>
        `;
        
        return `data:image/svg+xml;base64,${btoa(unescape(encodeURIComponent(svg)))}`;
    }
    
    /**
     * 初始化懒加载
     */
    initLazyLoading(avatars) {
        // 创建Intersection Observer
        this.imageObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    this.loadAvatar(img);
                    this.imageObserver.unobserve(img);
                }
            });
        }, {
            rootMargin: '50px' // 提前50px开始加载
        });
        
        // 观察所有头像
        avatars.forEach(img => this.imageObserver.observe(img));
    }
    
    /**
     * 初始化批次加载
     */
    initBatchLoading(avatars) {
        const batches = this.chunkArray(Array.from(avatars), this.options.batchSize);
        
        batches.forEach((batch, index) => {
            setTimeout(() => {
                batch.forEach(img => this.loadAvatar(img));
            }, index * this.options.batchDelay);
        });
    }
    
    /**
     * 加载单个头像
     */
    async loadAvatar(imgElement) {
        const originalSrc = imgElement.dataset.originalSrc;
        
        if (!originalSrc) {
            this.handleImageError(imgElement);
            return;
        }
        
        // 检查缓存
        if (this.loadedCache.has(originalSrc)) {
            this.setImageSuccess(imgElement, originalSrc);
            return;
        }
        
        try {
            // 尝试加载原始头像
            await this.loadImageWithRetry(originalSrc, this.options.retryTimes);
            this.loadedCache.set(originalSrc, true);
            this.setImageSuccess(imgElement, originalSrc);
            
        } catch (error) {
            console.warn(`Failed to load avatar: ${originalSrc}`, error);
            
            // 尝试加载备用头像
            const friendData = this.getFriendDataFromElement(imgElement);
            if (friendData && friendData.avatar_fallbacks) {
                await this.tryFallbackAvatars(imgElement, friendData.avatar_fallbacks);
            } else {
                this.handleImageError(imgElement);
            }
        }
    }
    
    /**
     * 带重试的图片加载
     */
    loadImageWithRetry(src, retries = 0) {
        return new Promise((resolve, reject) => {
            const img = new Image();
            
            const timer = setTimeout(() => {
                reject(new Error('Timeout'));
            }, this.options.timeout);
            
            img.onload = () => {
                clearTimeout(timer);
                resolve(src);
            };
            
            img.onerror = () => {
                clearTimeout(timer);
                if (retries > 0) {
                    setTimeout(() => {
                        this.loadImageWithRetry(src, retries - 1)
                            .then(resolve)
                            .catch(reject);
                    }, 1000);
                } else {
                    reject(new Error('Load failed'));
                }
            };
            
            img.src = src;
        });
    }
    
    /**
     * 尝试备用头像
     */
    async tryFallbackAvatars(imgElement, fallbacks) {
        for (const fallbackUrl of fallbacks) {
            try {
                await this.loadImageWithRetry(fallbackUrl);
                this.setImageSuccess(imgElement, fallbackUrl);
                return;
            } catch (error) {
                console.warn(`Fallback avatar failed: ${fallbackUrl}`);
            }
        }
        
        // 所有备用头像都失败
        this.handleImageError(imgElement);
    }
    
    /**
     * 设置图片加载成功
     */
    setImageSuccess(imgElement, src) {
        imgElement.src = src;
        imgElement.classList.remove(this.options.loadingClass);
        imgElement.classList.add(this.options.loadedClass);
    }
    
    /**
     * 处理图片加载错误
     */
    handleImageError(imgElement) {
        imgElement.classList.remove(this.options.loadingClass);
        imgElement.classList.add(this.options.errorClass);
        
        // 保持占位符或设置默认错误图片
        console.warn('Avatar load failed, using placeholder');
    }
    
    /**
     * 从元素获取友链数据
     */
    getFriendDataFromElement(imgElement) {
        // 尝试从最近的友链容器获取数据
        const container = imgElement.closest('[data-friend]');
        if (container && container.dataset.friend) {
            try {
                return JSON.parse(container.dataset.friend);
            } catch (e) {
                console.warn('Failed to parse friend data');
            }
        }
        return null;
    }
    
    /**
     * 数组分块
     */
    chunkArray(array, size) {
        const chunks = [];
        for (let i = 0; i < array.length; i += size) {
            chunks.push(array.slice(i, i + size));
        }
        return chunks;
    }
    
    /**
     * 销毁优化器
     */
    destroy() {
        if (this.imageObserver) {
            this.imageObserver.disconnect();
        }
        this.loadedCache.clear();
    }
}

// 全局实例
window.FriendlyLinksOptimizer = FriendlyLinksOptimizer;

// 自动初始化（可选）
document.addEventListener('DOMContentLoaded', () => {
    // 检查是否有友链元素
    if (document.querySelector('.friend-avatar, .reader-avatar, .friend-link img, .reader-wall img')) {
        const optimizer = new FriendlyLinksOptimizer();
        optimizer.init();
        
        // 保存到全局以便后续使用
        window.friendLinksOptimizer = optimizer;
    }
});

// 提供手动初始化方法
window.initFriendlyLinksOptimizer = (options = {}) => {
    const optimizer = new FriendlyLinksOptimizer(options);
    optimizer.init();
    return optimizer;
}; 
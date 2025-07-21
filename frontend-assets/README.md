# 友链前端优化资源

这个目录包含用于优化友链显示体验的前端资源。

## 📁 文件说明

- `friendly-links-optimizer.js` - 主要的JavaScript优化脚本
- `demo.html` - 使用示例
- `README.md` - 本说明文件

## 🚀 使用方法

### 1. **引入到你的博客**

将 `friendly-links-optimizer.js` 复制到你的博客静态资源目录，然后在模板中引入：

```html
<!-- 在友链页面或包含读者墙的页面引入 -->
<script src="/js/friendly-links-optimizer.js"></script>
```

### 2. **HTML结构要求**

确保你的友链HTML结构包含合适的类名：

```html
<!-- 友链列表 -->
<div class="friend-links">
    <div class="friend-item">
        <img class="friend-avatar" src="placeholder.jpg" data-src="real-avatar.jpg" alt="博主名">
        <div class="friend-info">
            <h4>博主名</h4>
            <p>博客描述</p>
        </div>
    </div>
</div>

<!-- 读者墙 -->
<div class="reader-wall">
    <img class="reader-avatar" src="placeholder.jpg" data-src="real-avatar.jpg" alt="读者名">
    <img class="reader-avatar" src="placeholder.jpg" data-src="real-avatar.jpg" alt="读者名">
</div>
```

### 3. **自动初始化**

脚本会自动检测页面中的友链元素并初始化优化。

### 4. **手动初始化**

如果需要自定义配置：

```javascript
// 自定义配置
const optimizer = window.initFriendlyLinksOptimizer({
    selector: '.my-avatar', // 自定义选择器
    batchSize: 5,          // 批次大小
    lazyLoad: true,        // 启用懒加载
    timeout: 10000         // 超时时间
});
```

## ⚙️ 配置选项

```javascript
{
    selector: '.friend-avatar, .reader-avatar', // 头像选择器
    loadingClass: 'avatar-loading',              // 加载中CSS类
    loadedClass: 'avatar-loaded',                // 加载完成CSS类  
    errorClass: 'avatar-error',                  // 加载错误CSS类
    batchSize: 3,                               // 批次加载大小
    batchDelay: 200,                            // 批次延迟(ms)
    retryTimes: 2,                              // 重试次数
    timeout: 8000,                              // 超时时间(ms)
    lazyLoad: true                              // 是否启用懒加载
}
```

## 🎨 CSS样式

脚本会自动注入优化样式，包括：

- 加载动画（shimmer效果）
- 淡入动画
- 错误状态样式

你也可以自定义这些样式：

```css
.avatar-loading {
    opacity: 0.6;
    /* 自定义加载样式 */
}

.avatar-loaded {
    opacity: 1;
    transition: all 0.3s ease;
    /* 自定义加载完成样式 */
}

.avatar-error {
    opacity: 0.7;
    filter: grayscale(50%);
    /* 自定义错误样式 */
}
```

## 🔧 高级用法

### 与后端优化数据配合

如果你的JSON包含优化数据（avatar_fallbacks等），可以这样使用：

```html
<div data-friend='{"avatar_fallbacks":["fallback1.jpg","fallback2.jpg"]}'>
    <img class="friend-avatar" data-src="original-avatar.jpg" alt="博主名">
</div>
```

### 动态加载友链

```javascript
// 动态添加友链后重新初始化
function addNewFriendLink(friendData) {
    // 添加HTML
    const html = `<div class="friend-item">...</div>`;
    friendLinksContainer.insertAdjacentHTML('beforeend', html);
    
    // 重新初始化优化器
    window.friendLinksOptimizer?.destroy();
    window.friendLinksOptimizer = window.initFriendlyLinksOptimizer();
}
```

## 🎯 效果

- ✅ 消除头像突然变化的闪烁
- ✅ 优雅的加载动画
- ✅ 自动重试失败的图片
- ✅ 智能使用备用头像
- ✅ 懒加载提升页面性能
- ✅ 批量加载避免阻塞

## 🔍 调试

打开浏览器控制台查看优化器的运行日志：

```
🚀 Friendly Links Optimizer initialized
Failed to load avatar: https://example.com/avatar.jpg
``` 
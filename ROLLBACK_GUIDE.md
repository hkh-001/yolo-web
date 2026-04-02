# 版本回退指南

## 📌 当前稳定版本

| 类型 | 名称 | Commit |
|------|------|--------|
| **标签** | `v5.2.2-stable` | `89faf6d` |
| **分支** | `stable-baseline` | `89faf6d` |

---

## 🔙 场景一：本地回退（推荐）

### 方式1：切换到稳定标签（只读，适合临时测试）
```bash
git checkout v5.2.2-stable
```

### 方式2：切换到稳定分支（可修改）
```bash
git checkout stable-baseline
```

### 方式3：强制重置当前分支到稳定版本（⚠️ 会丢失当前修改）
```bash
# 保存当前工作（如果有修改）
git stash

# 强制重置到稳定版本
git reset --hard v5.2.2-stable
```

---

## 🆕 场景二：从稳定版本创建新分支开发

```bash
# 从稳定标签创建新分支
git checkout -b feature/xxx v5.2.2-stable

# 或从稳定分支创建
git checkout stable-baseline
git checkout -b feature/xxx
```

---

## 🔥 场景三：紧急回退并覆盖远程（⚠️ 危险操作）

```bash
# 1. 切换到 main 分支
git checkout main

# 2. 强制重置到稳定版本
git reset --hard v5.2.2-stable

# 3. 强制推送到远程（会覆盖远程 main 分支）
git push origin main --force
```

---

## 📋 常用查询命令

```bash
# 查看所有标签
git tag -l

# 查看标签详情
git show v5.2.2-stable

# 查看提交历史
git log --oneline -10

# 对比当前与稳定版本的差异
git diff v5.2.2-stable

# 查看分支列表
git branch -a
```

---

## ⚠️ 注意事项

1. **标签（tag）是静态的** - 不会随新提交移动，永远指向 `89faf6d`
2. **分支（branch）是动态的** - 可以在上面继续开发
3. **强制回退前请确认** - 使用 `git status` 检查是否有未提交的修改

---

## 🚀 快速回退命令总结

```bash
# 最安全的回退方式（推荐）
git checkout v5.2.2-stable

# 或者
git checkout stable-baseline
```

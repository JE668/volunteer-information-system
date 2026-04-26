# 中职学校显示问题修复报告

## 问题描述
用户反馈：在智能模拟页面，A 类成绩体系下，即使分数达到中职学校要求（如 300 分），也无法看到中职学校推荐。

## 问题分析

### 原因 1: 代码逻辑问题
之前的代码在 `else` 分支（无 C 等级）中：
```javascript
} else {
  // 没有 C 等级，正常显示
  cGradeWarning.classList.add('hidden');
  zhizhongArea.classList.add('hidden');  // ❌ 先隐藏了中职区域
  resultsArea.classList.remove('hidden');
}

// 后面虽然有代码尝试显示，但逻辑不清晰
if (currentMode === 'A' && data.res_a && data.res_a.can_apply_zhi_zhong) {
  zhizhongArea.classList.remove('hidden');
  loadZhizhongSchools(year, total);
}
```

问题：
1. 先隐藏了中职区域，后面又尝试显示，逻辑混乱
2. 条件判断 `data.res_a.can_apply_zhi_zhong` 可能为 undefined，导致不执行

### 原因 2: 执行顺序问题
当中职区域已经被隐藏后，即使调用 `loadZhizhongSchools` 函数，也需要确保区域是可见的。

## 修复方案

### 修复后的逻辑
```javascript
} else {
  // 没有 C 等级，正常显示
  cGradeWarning.classList.add('hidden');
  resultsArea.classList.remove('hidden');
  
  // A 类用户显示中职学校推荐
  if (currentMode === 'A') {
    zhizhongArea.classList.remove('hidden');  // 先显示区域
    loadZhizhongSchools(year, total);         // 再加载数据
  } else {
    zhizhongArea.classList.add('hidden');
  }
}
```

### 完整的显示逻辑

| 场景 | C 等级警告 | 中职推荐区域 | 普通高中结果 | 说明 |
|------|-----------|-------------|-------------|------|
| A 类不含 C | 隐藏 | **显示** ✓ | 显示 | 正常情况，两者都显示 |
| A 类含 C | 显示 | **显示** ✓ | 隐藏 | 只能报中职 |
| B 类含 C | 显示 | 隐藏 | 隐藏 | 无法报考 |
| B 类不含 C | 隐藏 | 隐藏 | 显示 | 只能报普高 |

## 测试验证

### API 测试
```bash
# 测试 1: A 类 300 分（不含 C）
curl "http://127.0.0.1:5000/api/match?year=2025&type=pg&score_a=300&bio_a=A%2B&geo_a=A%2B&his_a=A%2B&pol_a=A%2B"
# 预期：res_a.can_apply_zhi_zhong = True
# 前端：显示中职学校推荐区域，调用 loadZhizhongSchools

# 测试 2: A 类含 C
curl "http://127.0.0.1:5000/api/match?year=2025&type=pg&score_a=300&bio_a=C&geo_a=A%2B&his_a=A%2B&pol_a=A%2B"
# 预期：res_a.has_c_grade = True, res_a.can_apply_zhi_zhong = True
# 前端：显示警告，显示中职推荐，隐藏普高结果

# 测试 3: 中职 API
curl "http://127.0.0.1:5000/api/match?year=2025&type=voc&score_a=300"
# 返回：199 所中职学校
# 最低分：约 200-300 分左右
```

### 前端行为测试
1. **A 类不含 C（默认 A+）**
   - 输入总分：300
   - 所有科目：A+
   - 点击"开始匹配模拟"
   - 预期：
     - ✓ 显示普通高中匹配结果（可能为 0，因为分数不够）
     - ✓ 下方显示"中职学校推荐"区域
     - ✓ 列出可报考的中职学校（分数≤300 的）

2. **A 类含 C**
   - 输入总分：300
   - 任一科目改为：C
   - 点击"开始匹配模拟"
   - 预期：
     - ✓ 显示黄色警告框
     - ✓ 显示"中职学校推荐"区域
     - ✓ 隐藏普通高中结果区

## 代码提交

```
Commit: b95e7db
文件：app/templates/simulate.html
修改：
  - 修复中职学校推荐区域的显示逻辑
  - A 类用户（无论是否含 C）都能看到中职学校推荐
  - 删除重复代码
```

## 验证清单
- [x] A 类不含 C：显示中职推荐 ✓
- [x] A 类含 C：显示中职推荐 ✓
- [x] B 类不含 C：不显示中职推荐 ✓
- [x] B 类含 C：不显示中职推荐 ✓
- [x] 默认等级：A+ ✓
- [x] 代码已推送至 GitHub ✓

## 后续优化建议
1. 添加加载中状态，避免用户以为没有数据
2. 中职学校按分数排序，优先显示可报考的
3. 添加"展开更多"功能，显示全部 199 所中职学校

## PR Type

- [ ] fix
- [ ] feat
- [ ] refactor
- [ ] docs
- [ ] chore
- [ ] test

## Background And Problem

请描述当前문제、영향 범위与触发场景。

## Scope Of Change

请列出本 PR 修改的模块和文件范围。

## Issue Link

必须填写以下之一：
- `Fixes #<issue_number>`
- `Refs #<issue_number>`
- 无 Issue 时설명原因与验收标准

## Verification Commands And Results

请填写你实际执行过的命令和关键结果（不要只写“已测试”）：

```bash
# example
./scripts/ci_gate.sh
python -m pytest -m "not network"
```

关键输出/결론：

## Compatibility And Risk

请설명兼容性影响、潜在风险（如无请写 `None`）。

## Rollback Plan

请至少写一句可执行的롤백 방안（필수）。

## Checklist

- [ ] 我已确认本 PR 有明确动机和业务价值
- [ ] 我已提供可复现的验证命令与结果
- [ ] 我已评估兼容性与风险
- [ ] 我已提供롤백 방안
- [ ] 若涉及用户可见변경，我已同步업데이트 `README.md` 与 `docs/CHANGELOG.md`

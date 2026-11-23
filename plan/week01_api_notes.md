# TerraGuide 第 1 周｜MediaWiki API 手动测试记录

测试日期：2026-11-23（北京时间）

共验证 5 项。以下请求均返回 HTTP 200，并逐项核对了 JSON 响应内容。

| 序号 | 测试项 | 请求链接 | 实际结果 | 结论 |
| --- | --- | --- | --- | --- |
| 1 | Boss 分类第一批 | [打开请求](https://terraria.wiki.gg/api.php?action=query&list=categorymembers&cmtitle=Category%3ABoss%20NPCs&cmnamespace=0&cmlimit=3&format=json&formatversion=2) | `query.categorymembers` 返回 3 条：`Bosses`、`Mechanical bosses`、`Betsy`。有 `continue` 对象。 | 通过。`Category:Boss NPCs` 可用于查询 Boss 分类成员。 |
| 2 | 武器分类第一批 | [打开请求](https://terraria.wiki.gg/api.php?action=query&list=categorymembers&cmtitle=Category%3AWeapon%20items&cmnamespace=0&cmlimit=3&format=json&formatversion=2) | `query.categorymembers` 返回 3 条：`List of weapons`、`Weapons`、`Hardmode weapons`。有 `continue` 对象。 | 通过。`Category:Weapon items` 可用于查询武器分类成员。 |
| 3 | 护甲分类第一批 | [打开请求](https://terraria.wiki.gg/api.php?action=query&list=categorymembers&cmtitle=Category%3AArmor%20sets&cmnamespace=0&cmlimit=3&format=json&formatversion=2) | `query.categorymembers` 返回 3 条：`Adamantite armor`、`Ancient Cobalt armor`、`Ancient Hallowed armor`。有 `continue` 对象。 | 通过。`Category:Armor sets` 可用于查询护甲分类成员。 |
| 4 | Boss 分类第二批 | [打开实际翻页请求](https://terraria.wiki.gg/api.php?action=query&list=categorymembers&cmtitle=Category%3ABoss%20NPCs&cmnamespace=0&cmlimit=3&format=json&formatversion=2&continue=-%7C%7C&cmcontinue=page%7C425241494e204f4620435448554c48550a425241494e204f4620435448554c4855%7C10805) | 返回 3 条：`Brain of Cthulhu`、`Celestial Pillars`、`Dark Mage`。与第一批的 `pageid` 无重复，并返回了新的 `continue` 对象。 | 通过。把第一批响应里的 `continue` 和 `cmcontinue` 都带入请求，可以得到下一批成员。 |
| 5 | 获取单页正文 | [打开 Betsy 正文请求](https://terraria.wiki.gg/api.php?action=parse&page=Betsy&prop=text&redirects=1&format=json&formatversion=2) | `parse.title` 为 `Betsy`，`parse.pageid` 为 `13003`，与第 1 项中的页面 ID 一致。`parse.text` 包含 `<div>`、`<table>` 等 HTML 标签。 | 通过。`action=parse&prop=text` 可以取得页面的 HTML 正文。 |

## 后续爬虫可用的规则

- 用 `action=query&list=categorymembers` 列出分类成员，从 `query.categorymembers` 读取页面标题和 ID。`cmlimit=3` 表示单次请求最多返回 3 条。
- 翻页时保留原查询参数，再传入上一批响应的 `continue` 对象中的全部字段。响应不再包含 `continue` 对象时结束翻页。
- 把选中的页面标题交给 `action=parse`，从 `parse.text` 读取 HTML。第 1 周的至少 100 页批量试跑另行记录。

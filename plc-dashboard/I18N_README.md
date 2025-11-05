# 多言語化（国際化）実装ガイド

このプロジェクトは、日本語、英語、中国語の3つの言語に対応しています。

## 📋 実装内容

### 1. インストール済みモジュール
- `@nuxtjs/i18n` - Nuxt 3用の国際化モジュール

### 2. サポート言語
- 🇯🇵 日本語 (ja) - デフォルト
- 🇺🇸 英語 (en)
- 🇨🇳 中国語 (zh)

### 3. 翻訳ファイルの場所
翻訳ファイルは `locales/` ディレクトリにあります：
- `locales/ja.json` - 日本語
- `locales/en.json` - 英語
- `locales/zh.json` - 中国語

## 🚀 使用方法

### ユーザー向け：言語の切り替え

1. 画面右上の言語切り替えボタン（地球アイコン）をクリック
2. 表示されるメニューから希望の言語を選択
3. 選択した言語は自動的に保存され、次回アクセス時も維持されます

### 開発者向け：新しいテキストの追加

#### 1. 翻訳キーを追加

各言語の翻訳ファイルに同じキーを追加します：

**locales/ja.json**
```json
{
  "mySection": {
    "title": "タイトル",
    "description": "説明文"
  }
}
```

**locales/en.json**
```json
{
  "mySection": {
    "title": "Title",
    "description": "Description"
  }
}
```

**locales/zh.json**
```json
{
  "mySection": {
    "title": "标题",
    "description": "描述"
  }
}
```

#### 2. Vueコンポーネントで使用

テンプレート内で `$t()` 関数を使用：

```vue
<template>
  <div>
    <h1>{{ $t('mySection.title') }}</h1>
    <p>{{ $t('mySection.description') }}</p>
  </div>
</template>
```

Script内で使用する場合：

```vue
<script setup>
const { t } = useI18n()

const message = t('mySection.title')
</script>
```

#### 3. パラメータ付き翻訳

動的な値を含む翻訳：

**翻訳ファイル**
```json
{
  "welcome": "こんにちは、{name}さん！",
  "itemCount": "{count}件のアイテム"
}
```

**使用例**
```vue
<template>
  <p>{{ $t('welcome', { name: 'John' }) }}</p>
  <p>{{ $t('itemCount', { count: 5 }) }}</p>
</template>
```

## 📁 プロジェクト構造

```
plc-dashboard/
├── locales/              # 翻訳ファイル
│   ├── ja.json          # 日本語
│   ├── en.json          # 英語
│   └── zh.json          # 中国語
├── components/
│   └── LanguageSwitch.vue  # 言語切り替えコンポーネント
├── pages/               # i18n対応済みページ
│   ├── index.vue
│   ├── login.vue
│   ├── errors-alarms.vue
│   ├── equipment/
│   │   └── [id].vue
│   └── monitoring/
│       └── [id].vue
└── nuxt.config.ts       # i18n設定
```

## 🔧 設定

`nuxt.config.ts` の i18n 設定：

```typescript
i18n: {
  locales: [
    { code: 'ja', iso: 'ja-JP', file: 'ja.json', name: '日本語' },
    { code: 'en', iso: 'en-US', file: 'en.json', name: 'English' },
    { code: 'zh', iso: 'zh-CN', file: 'zh.json', name: '中文' }
  ],
  lazy: true,
  langDir: 'locales',
  defaultLocale: 'ja',
  strategy: 'no_prefix',
  detectBrowserLanguage: {
    useCookie: true,
    cookieKey: 'i18n_redirected',
    redirectOn: 'root'
  }
}
```

## 📝 翻訳の追加手順

1. **キーの設計**
   - ネストした構造を使用して整理
   - 一貫性のある命名規則を使用
   - 例：`common.back`, `equipment.id`, `alarms.title`

2. **3つの言語すべてに追加**
   - ja.json（日本語）
   - en.json（英語）
   - zh.json（中国語）

3. **コンポーネントで使用**
   - テンプレート: `{{ $t('key') }}`
   - スクリプト: `t('key')`

4. **動作確認**
   - 各言語に切り替えて表示を確認
   - パラメータが正しく表示されるか確認

## 🌐 ブラウザ言語の自動検出

初回アクセス時、ユーザーのブラウザ言語設定を自動的に検出します：
- 日本語ブラウザ → 日本語表示
- 英語ブラウザ → 英語表示
- 中国語ブラウザ → 中国語表示
- その他 → 日本語（デフォルト）

## 🎯 ベストプラクティス

1. **一貫性のある構造**
   - 翻訳キーは階層的に整理
   - 同じカテゴリのテキストは同じセクションに配置

2. **完全性**
   - すべての言語で同じキーを定義
   - 欠落している翻訳があるとエラーになる可能性

3. **文脈を考慮**
   - 短い単語だけでなく、完全な文を翻訳
   - 文化的な違いを考慮

4. **テスト**
   - すべての言語で動作確認
   - レイアウトが崩れないか確認

## 🔍 トラブルシューティング

### 翻訳が表示されない
- 翻訳キーが3つの言語ファイルすべてに存在するか確認
- キーのスペルミスがないか確認
- 開発サーバーを再起動

### 言語が切り替わらない
- ブラウザのキャッシュをクリア
- localStorageをクリア（`localStorage.clear()`）
- Cookieを確認

## 📚 参考リンク

- [Nuxt i18n ドキュメント](https://i18n.nuxtjs.org/)
- [Vue I18n ドキュメント](https://vue-i18n.intlify.dev/)


import { cpSync, existsSync, mkdirSync, rmSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const sourceDir = join(__dirname, '..', '.output', 'public');
const targetDir = join(__dirname, '..', 'electron', 'renderer');

console.log('📦 Nuxt.js生成物をElectronにコピー中...');
console.log(`  ソース: ${sourceDir}`);
console.log(`  コピー先: ${targetDir}`);

// ソースディレクトリの存在確認
if (!existsSync(sourceDir)) {
  console.error('❌ エラー: .output/public/ が見つかりません');
  console.error('   先に "npm run generate" を実行してください');
  process.exit(1);
}

// 既存のrendererディレクトリを削除
if (existsSync(targetDir)) {
  console.log('🗑️  既存のrendererディレクトリを削除...');
  rmSync(targetDir, { recursive: true, force: true });
}

// rendererディレクトリを作成
mkdirSync(targetDir, { recursive: true });

// ファイルをコピー
try {
  cpSync(sourceDir, targetDir, { recursive: true });
  console.log('✅ コピー完了！');
  console.log(`   ${targetDir} に配置されました`);
} catch (error) {
  console.error('❌ コピーエラー:', error.message);
  process.exit(1);
}

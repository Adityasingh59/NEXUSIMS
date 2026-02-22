import fs from 'fs';
import path from 'path';

const cssTokenMap = {
    'var(--bg)': 'var(--color-ink)',
    'var(--bg-color)': 'var(--color-ink)',
    'var(--surface)': 'var(--color-surface)',
    'var(--surface-color)': 'var(--color-surface)',
    'var(--surface-hover)': 'var(--color-surface-2)',
    'var(--border)': 'var(--color-edge)',
    'var(--border-color)': 'var(--color-edge)',
    'var(--border-light)': 'var(--color-edge-2)',
    'var(--primary)': 'var(--color-blue)',
    'var(--primary-hover)': 'var(--color-blue-dark)',
    'var(--text)': 'var(--color-white)',
    'var(--text-color)': 'var(--color-white)',
    'var(--text-secondary)': 'var(--color-mist)',
    'var(--text-muted)': 'var(--color-slate)',
    'var(--success)': 'var(--color-green)',
    'var(--warning)': 'var(--color-amber)',
    'var(--danger)': 'var(--color-red)',
    'var(--info)': 'var(--color-blue)',
    'rgba(79, 70, 229, 0.15)': 'rgba(14, 167, 232, 0.15)', // Blue light
    'rgba(79, 70, 229, 0.4)': 'rgba(14, 167, 232, 0.4)', // Blue glow
};

function applyReplacements(content) {
    let newContent = content;
    for (const [old, replacement] of Object.entries(cssTokenMap)) {
        newContent = newContent.split(old).join(replacement);
    }
    return newContent;
}

function walkSync(dir, filelist = []) {
    const files = fs.readdirSync(dir);
    for (const file of files) {
        if (file === 'node_modules' || file === 'dist') continue;
        const filepath = path.join(dir, file);
        if (fs.statSync(filepath).isDirectory()) {
            filelist = walkSync(filepath, filelist);
        } else {
            if (file.endsWith('.css') || file.endsWith('.tsx') || file.endsWith('.ts')) {
                filelist.push(filepath);
            }
        }
    }
    return filelist;
}

const targetDir = process.cwd();
const filesToProcess = walkSync(path.join(targetDir, 'src'));

for (const file of filesToProcess) {
    const content = fs.readFileSync(file, 'utf8');
    const newContent = applyReplacements(content);
    if (content !== newContent) {
        fs.writeFileSync(file, newContent, 'utf8');
        console.log(`Updated ${file}`);
    }
}
console.log('Token replacement complete.');

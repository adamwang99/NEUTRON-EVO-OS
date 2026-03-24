// main.js
const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const fs = require('fs'); // Thêm module File System của Node.js

function createWindow() {
  const mainWindow = new BrowserWindow({
    width: 800,
    height: 600,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  mainWindow.loadFile('index.html');
  // mainWindow.webContents.openDevTools();
}

app.whenReady().then(() => {
  // === PHẦN CODE MỚI BẮT ĐẦU TỪ ĐÂY ===

  // Lắng nghe sự kiện 'create-file' từ renderer
  ipcMain.handle('create-file', async (event, data) => {
    try {
      // 1. Tạo nội dung file Markdown từ dữ liệu
      const markdownContent = `
# AI CODER TASK REQUIREMENTS
# Task: ${data.taskName}

---

## PART 1: GOLDEN RULES (MUST FOLLOW)

### 1.1. Preserve Existing Functionality
The following features are WORKING. You must **NOT** break them under any circumstances:
${data.guardFunctions.split('\n').map(line => `- ${line}`).join('\n')}

### 1.2. Mandatory Quality Checks
Before finishing, you MUST:
- **[${data.checkSyntax ? 'X' : ' '}] Syntax Check:** Review the ENTIRE syntax of all modified files.
- **[${data.checkLogic ? 'X' : ' '}] Logic Check:** Re-read the overall logic of affected files to ensure no regression.

---

## PART 2: TASK DESCRIPTION

${data.taskDesc}

---

## PART 3: CONTEXT & REMINDERS

### 3.1. Core Business Logic
Always keep these business rules in mind while coding:
${data.coreLogic.split('\n').map(line => `- ${line}`).join('\n')}

### 3.2. Technical Context
- **Project path:** ${data.projectPath}
- **Key files/folders involved:**
${data.relatedFiles.split('\n').map(line => `  - ${line}`).join('\n')}

---

## PART 4: BACKUP BEFORE LARGE CHANGES

Before making changes that affect multiple files or core logic, you MUST:
1. Remind the user: "Have you committed/backed up the project? You should do this before I proceed with large changes."
2. List the scope of impact — tell the user exactly which files will be modified.
3. Wait for user confirmation before proceeding.

**Definition of "large change":**
- Modifying 3 or more files at once
- Changing database structure, API contracts, or core business logic
- Deleting or moving files/directories
- Refactoring an entire module/component

---

## PART 5: VERSION MANAGEMENT

When making meaningful changes, you MUST update the version following **Semantic Versioning (MAJOR.MINOR.PATCH)**:

| Change Type | Bump | Example |
|---|---|---|
| Bug fix, minor patch | PATCH | 1.2.3 → 1.2.4 |
| New feature (non-breaking) | MINOR | 1.2.3 → 1.3.0 |
| Breaking API/structural change | MAJOR | 1.2.3 → 2.0.0 |

**Files to update (if they exist in the project):**
- \`package.json\` → \`"version"\` field
- \`pubspec.yaml\` → \`version:\` field
- \`setup.py\` / \`pyproject.toml\` → \`version\` field
- \`build.gradle\` → \`versionName\` / \`versionCode\`
- \`Info.plist\` → \`CFBundleShortVersionString\`

After updating, report clearly: "Version bumped from X.Y.Z → X.Y.Z+1 because [reason]."

---

## PART 6: POST-COMPLETION REQUIREMENTS
1. Provide a list of ALL files you have changed (full paths).
2. Briefly explain the logic behind each change.
3. (Important) If you detect any regression or potential risk, explain the cause and suggest a fix.
      `;

      // 2. Mở hộp thoại cho người dùng chọn nơi lưu file
      const { canceled, filePath } = await dialog.showSaveDialog({
        title: 'Lưu file mô tả nhiệm vụ',
        buttonLabel: 'Lưu',
        // Gợi ý tên file dựa trên tên nhiệm vụ
        defaultPath: path.join(app.getPath('documents'), `${data.taskName.replace(/[^a-z0-9]/gi, '_') || 'AI_Task'}.md`),
        filters: [
          { name: 'Markdown Files', extensions: ['md'] },
          { name: 'All Files', extensions: ['*'] }
        ]
      });

      if (canceled || !filePath) {
        return { success: false, message: 'Đã hủy lưu file.' };
      }

      // 3. Ghi file vào đĩa
      fs.writeFileSync(filePath, markdownContent.trim());

      return { success: true, message: `Đã tạo file thành công tại:\n${filePath}` };

    } catch (error) {
      console.error(error);
      return { success: false, message: `Lỗi khi tạo file: ${error.message}` };
    }
  });

  // === KẾT THÚC PHẦN CODE MỚI ===

  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
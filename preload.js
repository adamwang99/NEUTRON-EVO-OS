// preload.js
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  // Hàm 'createFile' sẽ gửi dữ liệu (data) đến kênh 'create-file'
  createFile: (data) => ipcRenderer.invoke('create-file', data)
});
// renderer.js
document.addEventListener('DOMContentLoaded', () => {
    let currentStep = 1;
    const totalSteps = 4;

    const btnBack = document.getElementById('btn-back');
    const btnNext = document.getElementById('btn-next');
    const btnGenerate = document.getElementById('btn-generate');

    function showStep(stepNumber) {
        for (let i = 1; i <= totalSteps; i++) {
            document.getElementById(`step-${i}`).style.display = 'none';
        }
        document.getElementById(`step-${stepNumber}`).style.display = 'block';

        btnBack.disabled = (stepNumber === 1);
        btnNext.style.display = (stepNumber === totalSteps) ? 'none' : 'inline-block';
        
        // Ẩn/Hiện nút Generate ở bước 4
        btnGenerate.style.display = (stepNumber === totalSteps) ? 'inline-block' : 'none';
    }

    btnNext.addEventListener('click', () => {
        if (currentStep < totalSteps) {
            currentStep++;
            showStep(currentStep);
        }
    });

    btnBack.addEventListener('click', () => {
        if (currentStep > 1) {
            currentStep--;
            showStep(currentStep);
        }
    });

    // === PHẦN CODE MỚI BẮT ĐẦU TỪ ĐÂY ===
    btnGenerate.addEventListener('click', async () => {
        // 1. Thu thập tất cả dữ liệu từ các form
        const data = {
            // Bước 1
            projectPath: document.getElementById('project-path').value,
            taskName: document.getElementById('task-name').value,
            taskDesc: document.getElementById('task-desc').value,
            // Bước 2
            coreLogic: document.getElementById('core-logic').value,
            relatedFiles: document.getElementById('related-files').value,
            // Bước 3
            backupConfirm: document.getElementById('backup-confirm').checked,
            guardFunctions: document.getElementById('guard-functions').value,
            checkSyntax: document.getElementById('check-syntax').checked,
            checkLogic: document.getElementById('check-logic').checked
        };

        // 2. Gửi dữ liệu đến main.js qua preload.js
        // (Kiểm tra xem 'electronAPI' đã được expose_chưa)
        if (window.electronAPI) {
            const result = await window.electronAPI.createFile(data);
            if (result.success) {
                alert(result.message); // Hiển thị thông báo thành công
            } else {
                alert(result.message); // Hiển thị thông báo lỗi hoặc hủy
            }
        } else {
            alert('Lỗi: electronAPI không được tìm thấy. Kiểm tra lại file preload.js.');
        }
    });
    // === KẾT THÚC PHẦN CODE MỚI ===


    // Hiển thị bước 1 ban đầu
    showStep(currentStep);
});
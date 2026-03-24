document.addEventListener('DOMContentLoaded', () => {
    let currentStep = 1;
    const totalSteps = 4;

    const btnBack = document.getElementById('btn-back');
    const btnNext = document.getElementById('btn-next');
    const btnGenerate = document.getElementById('btn-generate');

    function showStep(stepNumber) {
        // Ẩn tất cả các bước
        for (let i = 1; i <= totalSteps; i++) {
            document.getElementById(`step-${i}`).style.display = 'none';
        }

        // Hiện bước mong muốn
        document.getElementById(`step-${stepNumber}`).style.display = 'block';

        // Cập nhật trạng thái nút
        btnBack.disabled = (stepNumber === 1);
        btnNext.style.display = (stepNumber === totalSteps) ? 'none' : 'inline-block';
        
        // Ẩn nút Generate trừ khi đang ở bước 4
        if (stepNumber !== totalSteps) {
             btnGenerate.style.display = 'none';
        } else {
             btnGenerate.style.display = 'inline-block';
             btnNext.style.display = 'none'; // Ẩn nút Next ở bước cuối
        }
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

    // Tạm thời, nút Generate chưa làm gì
    btnGenerate.addEventListener('click', () => {
        alert('Chức năng "Tạo File" sẽ được thực hiện ở Task 2!');
        // Ở Task 2, chúng ta sẽ thu thập dữ liệu và gửi cho main.js tại đây
    });

    // Hiển thị bước 1 ban đầu
    showStep(currentStep);
});
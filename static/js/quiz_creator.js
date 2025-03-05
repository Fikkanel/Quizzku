// static/js/quiz_creator.js
let questionCount = 0;

function addQuestion() {
    questionCount++;
    
    // Pastikan questionsContainer ada sebelum memanipulasi
    const questionsContainer = document.getElementById('questionsContainer');
    if (!questionsContainer) {
        console.error('Kontainer pertanyaan tidak ditemukan');
        return;
    }

    const questionHtml = `
        <div class="question-box" id="question-${questionCount}">
            <button type="button" onclick="removeQuestion(${questionCount})" class="btn btn-remove">Hapus</button>
            <div class="form-group">
                <label>Pertanyaan:</label>
                <input type="text" class="form-control question-input" placeholder="Masukkan pertanyaan">
            </div>
            <div class="options-box">
                <div class="form-group">
                    <label>Pilihan Jawaban:</label>
                    <div class="option-input">
                        <label class="checkbox-container">
                            <input type="checkbox" name="correct-${questionCount}" value="0" onclick="handleCheckboxClick(this, ${questionCount})">
                            <span class="checkmark"></span>
                        </label>
                        <input type="text" class="form-control option-text" placeholder="Pilihan A">
                    </div>
                    <div class="option-input">
                        <label class="checkbox-container">
                            <input type="checkbox" name="correct-${questionCount}" value="1" onclick="handleCheckboxClick(this, ${questionCount})">
                            <span class="checkmark"></span>
                        </label>
                        <input type="text" class="form-control option-text" placeholder="Pilihan B">
                    </div>
                    <div class="option-input">
                        <label class="checkbox-container">
                            <input type="checkbox" name="correct-${questionCount}" value="2" onclick="handleCheckboxClick(this, ${questionCount})">
                            <span class="checkmark"></span>
                        </label>
                        <input type="text" class="form-control option-text" placeholder="Pilihan C">
                    </div>
                    <div class="option-input">
                        <label class="checkbox-container">
                            <input type="checkbox" name="correct-${questionCount}" value="3" onclick="handleCheckboxClick(this, ${questionCount})">
                            <span class="checkmark"></span>
                        </label>
                        <input type="text" class="form-control option-text" placeholder="Pilihan D">
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Tambahkan pengecekan sebelum insert
    try {
        questionsContainer.insertAdjacentHTML('beforeend', questionHtml);
    } catch (error) {
        console.error('Gagal menambahkan pertanyaan:', error);
    }
}

function handleCheckboxClick(checkbox, questionNumber) {
    // Pastikan checkbox ada
    if (!checkbox) return;

    // Temukan konteks pertanyaan
    const questionBox = document.getElementById(`question-${questionNumber}`);
    if (!questionBox) return;

    // Uncheck all other checkboxes in the same question
    const checkboxes = questionBox.querySelectorAll('input[type="checkbox"]');
    checkboxes.forEach(cb => {
        if (cb !== checkbox) {
            cb.checked = false;
        }
    });
}

function removeQuestion(id) {
    const questionElement = document.getElementById(`question-${id}`);
    if (questionElement) {
        questionElement.remove();
    }
}

function saveQuiz() {
    const quizCode = document.getElementById('quizCode');
    if (!quizCode) {
        alert('Elemen kode quiz tidak ditemukan!');
        return;
    }

    const quizCodeValue = quizCode.value.trim();
    if (!quizCodeValue) {
        alert('Mohon masukkan kode quiz!');
        return;
    }

    const questions = [];
    const questionBoxes = document.getElementsByClassName('question-box');
    
    if (questionBoxes.length === 0) {
        alert('Belum ada pertanyaan yang dibuat!');
        return;
    }

    for (const box of questionBoxes) {
        const questionInput = box.querySelector('.question-input');
        const optionInputs = box.querySelectorAll('.option-text');
        const correctCheckboxes = box.querySelectorAll('input[type="checkbox"]');
        
        if (!questionInput || optionInputs.length === 0 || correctCheckboxes.length === 0) {
            console.error('Elemen pertanyaan tidak lengkap');
            continue;
        }

        let correctAnswer = '';
        const options = [];
        
        optionInputs.forEach((input, index) => {
            const optionValue = input.value.trim();
            options.push(optionValue);
            if (correctCheckboxes[index].checked) {
                correctAnswer = optionValue;
            }
        });
        
        const questionValue = questionInput.value.trim();
        if (questionValue && options.every(opt => opt) && correctAnswer) {
            questions.push({
                question: questionValue,
                options: options,
                correct_answer: correctAnswer
            });
        }
    }

    if (questions.length === 0) {
        alert('Mohon isi minimal satu pertanyaan dengan lengkap!');
        return;
    }

    fetch('/save_quiz', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            quizCode: quizCodeValue,
            questions: questions
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Quiz berhasil disimpan!');
            window.location.href = '/';
        } else {
            alert(data.message || 'Gagal menyimpan quiz');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Terjadi kesalahan saat menyimpan quiz!');
    });
}

// Tambahkan event listener yang aman
document.addEventListener('DOMContentLoaded', function() {
    // Tambahkan tombol "Tambah Pertanyaan" jika belum ada
    const addQuestionBtn = document.getElementById('addQuestionBtn');
    if (addQuestionBtn) {
        addQuestionBtn.addEventListener('click', addQuestion);
    }

    // Tambahkan tombol "Simpan Quiz" jika belum ada
    const saveQuizBtn = document.getElementById('saveQuizBtn');
    if (saveQuizBtn) {
        saveQuizBtn.addEventListener('click', saveQuiz);
    }

    // Tambahkan pertanyaan pertama secara otomatis
    const questionsContainer = document.getElementById('questionsContainer');
    if (questionsContainer) {
        addQuestion();
    }
});
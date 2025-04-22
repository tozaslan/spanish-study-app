const numLessonsInput = document.getElementById('num-lessons');
const generateBtn = document.getElementById('generate-btn');
const resultsDiv = document.getElementById('results');
const loadingDiv = document.getElementById('loading');
const errorDiv = document.getElementById('error-message');

// Define the backend URL (Flask default)
const BACKEND_URL = 'http://127.0.0.1:5000'; // Adjust if your backend runs elsewhere

generateBtn.addEventListener('click', async () => {
    const n = numLessonsInput.value;
    resultsDiv.innerHTML = ''; // Clear previous results
    errorDiv.textContent = ''; // Clear previous errors
    loadingDiv.style.display = 'block'; // Show loading indicator
    generateBtn.disabled = true;

    try {
        // Fetch exercises from the backend
        const response = await fetch(`${BACKEND_URL}/generate-exercises?lessons=${n}`);
        const data = await response.json(); // Parse JSON response

        if (!response.ok) {
            // Handle HTTP errors reported by the backend
            throw new Error(data.error || `Error ${response.status}: ${response.statusText}`);
        }

        // --- ** FINAL DISPLAY CODE START ** ---

        // Display the success message from the backend
        if (data.message) {
            const messageElement = document.createElement('h3');
            messageElement.textContent = data.message;
            resultsDiv.appendChild(messageElement);
        }

        // Check if the exercises array exists and display them
        if (data.exercises && Array.isArray(data.exercises) && data.exercises.length > 0) {
            data.exercises.forEach((ex, index) => {
                const exerciseElement = document.createElement('div');
                exerciseElement.classList.add('exercise');
                exerciseElement.style.border = '1px solid #eee';
                exerciseElement.style.padding = '10px';
                exerciseElement.style.marginBottom = '15px';

                let contentHTML = `<p><strong>Ejercicio ${index + 1} (${ex.type || 'N/A'}):</strong></p>`;
                contentHTML += `<p>${ex.question || 'Pregunta no encontrada.'}</p>`;

                if (ex.type === 'multiple-choice' && ex.options && Array.isArray(ex.options)) {
                    contentHTML += '<ul>';
                    ex.options.forEach(option => {
                        contentHTML += `<li>${option}</li>`;
                    });
                    contentHTML += '</ul>';
                }

                // Optionally display the answer (e.g., hidden initially or for review)
                // You could add a button here to reveal the answer
                contentHTML += `<p><em>Respuesta: ${ex.answer || 'N/A'}</em></p>`; // Simple display for now

                exerciseElement.innerHTML = contentHTML;
                resultsDiv.appendChild(exerciseElement);
            });
        } else {
            // Handle case where backend succeeded but no exercises were returned
            const noExercisesElement = document.createElement('p');
            noExercisesElement.textContent = "(No se generaron ejercicios.)";
            resultsDiv.appendChild(noExercisesElement);
        }

        // --- ** FINAL DISPLAY CODE END ** ---

    } catch (error) {
        console.error("Error processing backend response:", error);
        errorDiv.textContent = `Error al generar ejercicios: ${error.message}`;
        resultsDiv.innerHTML = ''; // Clear results on error
    } finally {
        loadingDiv.style.display = 'none'; // Hide loading indicator
        generateBtn.disabled = false;
    }
});
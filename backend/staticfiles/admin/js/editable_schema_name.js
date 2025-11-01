/**
 * Editable Schema Name Widget JavaScript
 * Handles the edit and confirm functionality for schema_name field
 * Integrates with Unfold admin theme
 */
(function() {
    'use strict';

    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initEditableSchemaName);
    } else {
        initEditableSchemaName();
    }

    function initEditableSchemaName() {
        const wrappers = document.querySelectorAll('.editable-schema-wrapper');

        wrappers.forEach(function(wrapper) {
            const input = wrapper.querySelector('.editable-schema-name');
            const editBtn = wrapper.querySelector('.edit-schema-btn');
            const confirmBtn = wrapper.querySelector('.confirm-schema-btn');

            if (!input || !editBtn || !confirmBtn) return;

            // Store original value
            let originalValue = input.value;

            // Edit button click handler
            editBtn.addEventListener('click', function(e) {
                e.preventDefault();

                // Enable the input
                input.removeAttribute('readonly');
                input.focus();

                // Show confirm button, hide edit button (using Tailwind classes)
                editBtn.classList.add('hidden');
                confirmBtn.classList.remove('hidden');
            });

            // Confirm button click handler
            confirmBtn.addEventListener('click', function(e) {
                e.preventDefault();

                // Disable the input
                input.setAttribute('readonly', 'readonly');

                // Show edit button, hide confirm button
                confirmBtn.classList.add('hidden');
                editBtn.classList.remove('hidden');

                // Update original value
                originalValue = input.value;

                // Show success message
                showSuccessMessage('Schema name updated successfully');
            });

            // Handle Escape key to cancel editing
            input.addEventListener('keydown', function(e) {
                if (e.key === 'Escape') {
                    e.preventDefault();

                    // Restore original value
                    input.value = originalValue;

                    // Reset state
                    input.setAttribute('readonly', 'readonly');
                    confirmBtn.classList.add('hidden');
                    editBtn.classList.remove('hidden');
                }

                // Handle Enter key to confirm
                if (e.key === 'Enter') {
                    e.preventDefault();
                    confirmBtn.click();
                }
            });
        });
    }

    function showSuccessMessage(message) {
        // Create notification with Unfold/Tailwind styling
        const notification = document.createElement('div');
        notification.className = 'schema-notification fixed top-5 right-5 bg-green-600 text-white px-6 py-3 rounded-lg shadow-lg z-50 flex items-center gap-2 text-sm font-medium';

        // Add check icon
        notification.innerHTML = `
            <span class="material-symbols-outlined" style="font-size: 20px;">check_circle</span>
            <span>${message}</span>
        `;

        document.body.appendChild(notification);

        // Remove after 3 seconds
        setTimeout(function() {
            notification.classList.add('closing');
            setTimeout(function() {
                if (notification.parentNode) {
                    document.body.removeChild(notification);
                }
            }, 300);
        }, 3000);
    }
})();

"""
Custom widgets for tenant admin
"""
from django import forms
from django.forms.utils import flatatt
from django.utils.html import format_html


class EditableSchemaNameWidget(forms.TextInput):
    """
    Custom widget for schema_name field with edit/confirm icons.
    Field is readonly by default, can be enabled by clicking edit icon.
    Uses Unfold's Tailwind CSS classes for consistent styling.
    """

    def __init__(self, attrs=None):
        # Unfold text input classes
        unfold_classes = (
            'border bg-white font-medium min-w-20 rounded-md shadow-sm text-gray-500 text-sm '
            'focus:ring focus:ring-primary-300 focus:border-primary-600 focus:outline-none '
            'group-[.errors]:border-red-600 group-[.errors]:focus:ring-red-200 '
            'dark:bg-gray-900 dark:border-gray-700 dark:text-gray-400 '
            'dark:focus:border-primary-600 dark:focus:ring-primary-700 dark:focus:ring-opacity-50 '
            'dark:group-[.errors]:border-red-500 dark:group-[.errors]:focus:ring-red-600/40 '
            'px-3 py-2 w-full max-w-2xl editable-schema-name'
        )

        default_attrs = {
            'class': unfold_classes,
            'readonly': 'readonly',
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)

    class Media:
        css = {
            'all': ('admin/css/editable_schema_name.css',)
        }
        js = ('admin/js/editable_schema_name.js',)

    def render(self, name, value, attrs=None, renderer=None):
        """Render the widget with edit and confirm icons"""
        if value is None:
            value = ''

        final_attrs = self.build_attrs(self.attrs, attrs)
        if value != '':
            final_attrs['value'] = value

        # Build the input field HTML manually
        input_html = format_html('<input type="text" name="{}" {}>', name, flatatt(final_attrs))

        # Wrap with icons using Tailwind classes
        html = format_html(
            '''
            <div class="flex items-center gap-3 editable-schema-wrapper">
                {}
                <button type="button" class="edit-schema-btn flex items-center justify-center p-1.5 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors" title="Edit schema name">
                    <span class="material-symbols-outlined text-primary-600 dark:text-primary-400" style="font-size: 20px;">edit</span>
                </button>
                <button type="button" class="confirm-schema-btn hidden flex items-center justify-center p-1.5 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors" title="Confirm changes">
                    <span class="material-symbols-outlined text-green-600 dark:text-green-400" style="font-size: 20px;">check_circle</span>
                </button>
            </div>
            ''',
            input_html
        )
        return html

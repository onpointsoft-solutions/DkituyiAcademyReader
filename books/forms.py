from django import forms
from .models import Book, Author, Category, BookChapter, BookPage


class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = [
            'title', 'subtitle', 'author', 'categories', 'description',
            'isbn', 'publication_date', 'language', 'pages',
            'content_source', 'pdf_file', 'manual_content',
            'price', 'is_free', 'cover_url'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter book title'}),
            'subtitle': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter subtitle (optional)'}),
            'author': forms.Select(attrs={'class': 'form-control'}),
            'categories': forms.CheckboxSelectMultiple(),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Enter book description'}),
            'isbn': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter ISBN (optional)'}),
            'publication_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'language': forms.Select(attrs={'class': 'form-control'}),
            'pages': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'content_source': forms.Select(attrs={'class': 'form-control'}),
            'manual_content': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 10, 
                'placeholder': 'Paste the full book content here if not using PDF file. You can organize it into chapters and pages later.',
                'style': 'display: none;'  # Hidden by default, shown when manual is selected
            }),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': 0}),
            'is_free': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'cover_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'Enter cover image URL (optional)'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['author'].queryset = Author.objects.all().order_by('name')
        self.fields['categories'].queryset = Category.objects.all().order_by('name')
        
        # Add help text for manual content
        self.fields['manual_content'].help_text = (
            "Enter the complete book content here. You can organize it into chapters and pages "
            "after creating the book. This is useful when you don't have a PDF file but want "
            "to provide structured content for reading and tracking."
        )


class ChapterForm(forms.ModelForm):
    class Meta:
        model = BookChapter
        fields = ['title', 'chapter_number', 'pages_count', 'content', 'is_free']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter chapter title'}),
            'chapter_number': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'pages_count': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'content': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 15, 
                'placeholder': 'Enter the full content for this chapter. You can break it into pages below.'
            }),
            'is_free': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['content'].help_text = (
            "Enter the complete content for this chapter. This will be the main reading material. "
            "You can optionally break this content into specific pages for better tracking and navigation."
        )


class PageForm(forms.ModelForm):
    class Meta:
        model = BookPage
        fields = ['page_number', 'content']
        widgets = {
            'page_number': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'content': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 10, 
                'placeholder': 'Enter the content for this specific page.'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['content'].help_text = (
            "Enter the content for this specific page. This allows for precise tracking "
            "of reading progress and enables page-by-page navigation for readers."
        )


class QuickChapterForm(forms.ModelForm):
    """Quick form for adding chapters with auto-numbering"""
    class Meta:
        model = BookChapter
        fields = ['title', 'content', 'is_free']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter chapter title'}),
            'content': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 8, 
                'placeholder': 'Enter chapter content'
            }),
            'is_free': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class QuickPageForm(forms.ModelForm):
    """Quick form for adding pages with auto-numbering"""
    class Meta:
        model = BookPage
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 6, 
                'placeholder': 'Enter page content'
            }),
        }


class BulkContentForm(forms.Form):
    """Form for bulk content import"""
    content = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control', 
            'rows': 20, 
            'placeholder': 'Paste your entire book content here. Use "Chapter X: Title" format to separate chapters.'
        }),
        help_text="Paste your entire book content here. Use 'Chapter X: Title' format to automatically separate chapters."
    )
    
    def clean_content(self):
        content = self.cleaned_data['content']
        if not content.strip():
            raise forms.ValidationError("Content cannot be empty.")
        return content

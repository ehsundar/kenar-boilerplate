from django import forms


class CreateProductForm(forms.Form):
    name = forms.CharField(max_length=50, label="نام محصول")
    price = forms.IntegerField(min_value=0, step_size=1000, label="قیمت واحد")
    content = forms.FileField(label="محتوی قابل فروش")

import logging

import kenar
import pydantic
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import urlencode
from django.views import View
from django.views.generic import TemplateView
from kenar import Scope, OauthResourceType
from rest_framework.decorators import api_view

from addon.forms import CreateProductForm
from addon.models import Post, DivarUsers, Product
from boilerplate import settings
from boilerplate.clients import get_divar_kenar_client
from oauth.models import OAuth
from oauth.schemas import OAuthSession, OAuthSessionType

logger = logging.getLogger(__name__)


class LandingView(TemplateView):
    template_name = "landing.html"

    def get_context_data(self, **kwargs):
        post_token = self.request.GET.get("post_token")
        post, _ = Post.objects.get_or_create(token=post_token)

        oauth_session = OAuthSession(
            callback_url=reverse("product_create"),
            type=OAuthSessionType.POST,
            post_token=post_token,
        )
        self.request.session[settings.OAUTH_SESSION_KEY] = oauth_session.model_dump(exclude_none=True)

        kenar_client = get_divar_kenar_client()

        oauth_scopes = [
            Scope(resource_type=OauthResourceType.USER_PHONE),
            Scope(resource_type=OauthResourceType.POST_ADDON_CREATE, resource_id=post_token),
        ]

        oauth_url = kenar_client.oauth.get_oauth_redirect(
            scopes=oauth_scopes,
            state=oauth_session.state,
        )

        return {
            "oauth_redirect": oauth_url,
        }


class CreateProductView(View):
    def get(self, request, *args, **kwargs):
        try:
            oauth = OAuth.objects.get(session_id=request.session.session_key)
            post = oauth.post
        except OAuth.DoesNotExist:
            return HttpResponseForbidden("permission denied")

        kenar_client = get_divar_kenar_client()

        user = kenar_client.finder.get_user(oauth.access_token)
        DivarUsers.objects.get_or_create(phone=user.phone_numbers[0])

        form = CreateProductForm()
        return render(request, "upload.html", {
            "form": form,
            "phone": user.phone_numbers[0],
        })

    def post(self, request, *args, **kwargs):
        form = CreateProductForm(request.POST, request.FILES)
        if not form.is_valid():
            return render(request, "upload.html", {
                "form": form,
            })

        try:
            oauth = OAuth.objects.get(session_id=request.session.session_key)
            post = oauth.post
        except OAuth.DoesNotExist:
            return HttpResponseForbidden("permission denied")

        kenar_client = get_divar_kenar_client()

        user = kenar_client.finder.get_user(oauth.access_token)
        u = DivarUsers.objects.get(phone=user.phone_numbers[0])

        p = Product.objects.create(
            owner=u,
            name=form.cleaned_data.get("name"),
            price=form.cleaned_data.get("price"),
            content=form.cleaned_data.get("content"),
        )

        post_addon = kenar.CreatePostAddonRequest(
            token=post.token,
            widgets=[
                kenar.LegendTitleRow(
                    title="فروش ویژه",
                    subtitle="محصولات دانلودی",
                    image_url="logo",
                    tags=[],
                ),
                kenar.WideButtonBar(
                    button=kenar.WideButtonBar.Button(
                        title="خرید محصول",
                        link=f"https://dl-addon.darkube.app/addon/buy/{p.id}"
                    ),
                ),
            ]
        )
        kenar_client.addon.create_post_addon(oauth.access_token, post_addon)

        return redirect(reverse("app_close"))


class AppClose(TemplateView):
    template_name = "app_close.html"


@api_view(["GET"])
def addon_oauth(request):
    post_token = request.query_params.get("post_token")
    callback_url = request.query_params.get("return_url")

    post, _ = Post.objects.get_or_create(token=post_token)

    callback_url = request.build_absolute_uri(callback_url)

    oauth_session = OAuthSession(
        callback_url=callback_url,
        type=OAuthSessionType.POST,
        post_token=post.token,
    )
    request.session[settings.OAUTH_SESSION_KEY] = oauth_session.model_dump(exclude_none=True)

    kenar_client = get_divar_kenar_client()

    oauth_scopes = [
        Scope(resource_type=OauthResourceType.USER_PHONE),
        Scope(resource_type=OauthResourceType.POST_ADDON_CREATE, resource_id=post_token),
    ]

    oauth_url = kenar_client.oauth.get_oauth_redirect(
        scopes=oauth_scopes,
        state=oauth_session.state,
    )

    return redirect(oauth_url)


@api_view(["GET"])
def addon_app(request):
    try:
        oauth_session = OAuthSession(**request.session.get(settings.OAUTH_SESSION_KEY))
    except pydantic.ValidationError as e:
        logger.error(e)
        return HttpResponseForbidden("permission denied")

    req_state = request.query_params.get("state")
    if not req_state or req_state != oauth_session.get_state():
        return HttpResponseForbidden("permission denied")

    try:
        oauth = OAuth.objects.get(session_id=request.session.session_key)
    except OAuth.DoesNotExist:
        return HttpResponseForbidden("permission denied")

    # After processing the post logic, redirect to the callback URL
    callback_url = oauth_session.get_callback_url()
    return redirect(callback_url)

import logging

import kenar
import pydantic
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import urlencode
from django.views.generic import TemplateView
from kenar import Scope, OauthResourceType
from rest_framework.decorators import api_view

from addon.models import Post
from boilerplate import settings
from boilerplate.clients import get_divar_kenar_client
from oauth.models import OAuth
from oauth.schemas import OAuthSession, OAuthSessionType

logger = logging.getLogger(__name__)


class LandingView(TemplateView):
    template_name = "landing.html"

    def get_context_data(self, **kwargs):
        post_token = self.request.GET.get("post_token")
        oauth_params = {
            "post_token": post_token,
            "return_url": reverse("addon_app"),
        }
        return {
            "oauth_redirect": f"{reverse("start_app")}?{urlencode(oauth_params)}",
        }


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
        post = oauth.post
    except OAuth.DoesNotExist:
        return HttpResponseForbidden("permission denied")

    kenar_client = get_divar_kenar_client()

    post_addon = kenar.CreatePostAddonRequest(
        token=post.token,
        widgets=[
            kenar.LegendTitleRow(
                title="فروش ویژه",
                subtitle="محصولات دانلودی",
                image_url="logo",
                tags=[],
            )
        ]
    )
    kenar_client.addon.create_post_addon(oauth.access_token, post_addon)

    # After processing the post logic, redirect to the callback URL
    callback_url = oauth_session.get_callback_url()
    return redirect(callback_url)

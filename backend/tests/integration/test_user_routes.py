# tests/integration/test_user_routes.py

class TestGetUser:
    def test_returns_public_profile(self, client, amina):
        response = client.get(f"/api/users/{amina['user']['id']}")
        assert response.status_code == 200
        assert response.get_json()["username"] == "amina"

    def test_does_not_expose_email(self, client, amina):
        # UserPublicSchema deliberately excludes email -- this is the
        # HTTP-level proof that the public route actually uses that
        # schema and not the full UserSchema.
        response = client.get(f"/api/users/{amina['user']['id']}")
        assert "email" not in response.get_json()

    def test_unknown_user_returns_404(self, client):
        response = client.get("/api/users/999999")
        assert response.status_code == 404


class TestUpdateProfile:
    def test_requires_auth(self, client):
        response = client.put("/api/users/me/profile", json={"first_name": "X"})
        assert response.status_code == 401

    def test_creates_profile_on_first_call(self, client, amina):
        response = client.put(
            "/api/users/me/profile", headers=amina["headers"], json={"first_name": "Amina", "bio": "Maize farmer"}
        )
        assert response.status_code == 200
        assert response.get_json()["first_name"] == "Amina"

    def test_updates_profile_on_second_call(self, client, amina):
        client.put("/api/users/me/profile", headers=amina["headers"], json={"first_name": "First"})
        response = client.put("/api/users/me/profile", headers=amina["headers"], json={"first_name": "Second"})
        assert response.get_json()["first_name"] == "Second"


class TestUpdateLanguage:
    def test_requires_auth(self, client):
        response = client.put("/api/users/me/language", json={"language": "sw"})
        assert response.status_code == 401

    def test_updates_to_kiswahili(self, client, amina):
        response = client.put("/api/users/me/language", headers=amina["headers"], json={"language": "sw"})
        assert response.status_code == 200
        assert response.get_json()["language"] == "sw"

    def test_persists_across_requests(self, client, amina):
        client.put("/api/users/me/language", headers=amina["headers"], json={"language": "sw"})
        me = client.get("/api/auth/me", headers=amina["headers"])
        assert me.get_json()["language"] == "sw"

    def test_rejects_unsupported_language(self, client, amina):
        response = client.put("/api/users/me/language", headers=amina["headers"], json={"language": "fr"})
        assert response.status_code == 422

    def test_rejects_missing_language(self, client, amina):
        response = client.put("/api/users/me/language", headers=amina["headers"], json={})
        assert response.status_code == 422


class TestFollow:
    def test_follow_and_unfollow(self, client, amina, brian):
        follow_response = client.post(f"/api/users/{brian['user']['id']}/follow", headers=amina["headers"])
        assert follow_response.status_code == 201

        unfollow_response = client.delete(f"/api/users/{brian['user']['id']}/follow", headers=amina["headers"])
        assert unfollow_response.status_code == 204

    def test_follow_requires_auth(self, client, brian):
        response = client.post(f"/api/users/{brian['user']['id']}/follow")
        assert response.status_code == 401

    def test_following_twice_returns_409(self, client, amina, brian):
        client.post(f"/api/users/{brian['user']['id']}/follow", headers=amina["headers"])
        response = client.post(f"/api/users/{brian['user']['id']}/follow", headers=amina["headers"])
        assert response.status_code == 409

    def test_following_self_returns_422(self, client, amina):
        response = client.post(f"/api/users/{amina['user']['id']}/follow", headers=amina["headers"])
        assert response.status_code == 422

    def test_unfollowing_without_following_returns_404(self, client, amina, brian):
        response = client.delete(f"/api/users/{brian['user']['id']}/follow", headers=amina["headers"])
        assert response.status_code == 404


class TestListUsers:
    def test_lists_all_users_by_default(self, client, amina, brian):
        response = client.get("/api/users")
        assert response.status_code == 200
        usernames = {u["username"] for u in response.get_json()}
        assert {"amina", "brian"} <= usernames

    def test_filters_by_role(self, client, register_user):
        register_user(username="farmerx", role="farmer")
        register_user(username="expertx", role="expert")

        response = client.get("/api/users?role=expert")
        usernames = {u["username"] for u in response.get_json()}
        assert "expertx" in usernames
        assert "farmerx" not in usernames

    def test_search_matches_username(self, client, amina, brian):
        response = client.get("/api/users?search=ami")
        usernames = {u["username"] for u in response.get_json()}
        assert "amina" in usernames
        assert "brian" not in usernames

    def test_search_matches_profile_first_name(self, client, amina):
        client.put("/api/users/me/profile", headers=amina["headers"], json={"first_name": "Zawadi"})
        response = client.get("/api/users?search=Zawadi")
        usernames = {u["username"] for u in response.get_json()}
        assert "amina" in usernames

    def test_does_not_require_auth(self, client):
        response = client.get("/api/users")
        assert response.status_code == 200


class TestUserPosts:
    def test_lists_only_that_users_posts_newest_first(self, client, amina, brian):
        client.post("/api/posts", headers=amina["headers"], json={"title": "Amina 1", "content": "c"})
        client.post("/api/posts", headers=brian["headers"], json={"title": "Brian 1", "content": "c"})
        client.post("/api/posts", headers=amina["headers"], json={"title": "Amina 2", "content": "c"})

        response = client.get(f"/api/users/{amina['user']['id']}/posts")
        assert response.status_code == 200
        titles = [p["title"] for p in response.get_json()]
        assert titles == ["Amina 2", "Amina 1"]

    def test_unknown_user_returns_404(self, client):
        response = client.get("/api/users/999999/posts")
        assert response.status_code == 404

    def test_does_not_require_auth(self, client, amina):
        response = client.get(f"/api/users/{amina['user']['id']}/posts")
        assert response.status_code == 200

    def test_liked_by_me_reflects_authenticated_viewer(self, client, amina, brian):
        post_id = client.post(
            "/api/posts", headers=amina["headers"], json={"title": "T", "content": "c"}
        ).get_json()["id"]
        client.post(f"/api/posts/{post_id}/like", headers=brian["headers"])

        response = client.get(f"/api/users/{amina['user']['id']}/posts", headers=brian["headers"])
        post = response.get_json()[0]
        assert post["liked_by_me"] is True
        assert post["like_count"] == 1

        anonymous_response = client.get(f"/api/users/{amina['user']['id']}/posts")
        assert anonymous_response.get_json()[0]["liked_by_me"] is False


class TestFollowingAndFollowerCount:
    def test_my_following_requires_auth(self, client):
        response = client.get("/api/users/me/following")
        assert response.status_code == 401

    def test_my_following_lists_followed_ids(self, client, amina, brian):
        client.post(f"/api/users/{brian['user']['id']}/follow", headers=amina["headers"])
        response = client.get("/api/users/me/following", headers=amina["headers"])
        assert response.status_code == 200
        assert response.get_json()["following_ids"] == [brian["user"]["id"]]

    def test_followers_count_does_not_require_auth(self, client, amina, brian):
        client.post(f"/api/users/{brian['user']['id']}/follow", headers=amina["headers"])
        response = client.get(f"/api/users/{brian['user']['id']}/followers/count")
        assert response.status_code == 200
        assert response.get_json()["count"] == 1

    def test_followers_count_zero_for_unfollowed_user(self, client, amina):
        response = client.get(f"/api/users/{amina['user']['id']}/followers/count")
        assert response.get_json()["count"] == 0

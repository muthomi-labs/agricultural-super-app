# tests/unit/test_user_service.py

import pytest

from app.errors import ConflictError, NotFoundError, ValidationAPIError
from app.services import user_service


class TestGetUserOr404:
    def test_returns_existing_user(self, create_user):
        created = create_user(username="amina")
        found = user_service.get_user_or_404(created.id)
        assert found.id == created.id

    def test_raises_not_found_for_missing_user(self):
        with pytest.raises(NotFoundError):
            user_service.get_user_or_404(999999)


class TestUpdateLanguage:
    def test_defaults_to_english(self, create_user):
        user = create_user(username="amina")
        assert user.language == "en"

    def test_updates_to_kiswahili(self, create_user):
        user = create_user(username="amina")
        updated = user_service.update_language(user, "sw")
        assert updated.language == "sw"
        assert user.language == "sw"  # same row, mutated in place

    def test_persists_across_a_fresh_lookup(self, create_user):
        user = create_user(username="amina")
        user_service.update_language(user, "sw")
        reloaded = user_service.get_user_or_404(user.id)
        assert reloaded.language == "sw"


class TestUpsertOwnProfile:
    def test_creates_profile_when_none_exists(self, create_user):
        user = create_user(username="amina")
        assert user.profile is None

        profile = user_service.upsert_own_profile(user, {"first_name": "Amina", "bio": "Maize farmer"})

        assert profile.user_id == user.id
        assert profile.first_name == "Amina"
        assert profile.bio == "Maize farmer"

    def test_updates_existing_profile_in_place(self, create_user):
        user = create_user(username="amina")
        first = user_service.upsert_own_profile(user, {"first_name": "Amina"})
        second = user_service.upsert_own_profile(user, {"first_name": "Updated"})

        # Same row updated, not a second profile created -- profiles.user_id
        # is unique, so a second insert would raise IntegrityError if this
        # were broken.
        assert first.id == second.id
        assert second.first_name == "Updated"


class TestFollowUser:
    def test_creates_follow_relationship(self, create_user):
        amina = create_user(username="amina")
        brian = create_user(username="brian")

        follow = user_service.follow_user(amina, brian.id)

        assert follow.follower_id == amina.id
        assert follow.following_id == brian.id

    def test_cannot_follow_self(self, create_user):
        amina = create_user(username="amina")
        with pytest.raises(ValidationAPIError):
            user_service.follow_user(amina, amina.id)

    def test_cannot_follow_same_user_twice(self, create_user):
        amina = create_user(username="amina")
        brian = create_user(username="brian")
        user_service.follow_user(amina, brian.id)

        with pytest.raises(ConflictError):
            user_service.follow_user(amina, brian.id)

    def test_following_nonexistent_user_raises_not_found(self, create_user):
        amina = create_user(username="amina")
        with pytest.raises(NotFoundError):
            user_service.follow_user(amina, 999999)


class TestUnfollowUser:
    def test_removes_existing_follow(self, create_user):
        amina = create_user(username="amina")
        brian = create_user(username="brian")
        user_service.follow_user(amina, brian.id)

        user_service.unfollow_user(amina, brian.id)  # should not raise

        # Following again should succeed, proving the row was actually
        # deleted rather than e.g. soft-marked in a way follow_user's
        # duplicate check would still catch.
        user_service.follow_user(amina, brian.id)

    def test_unfollowing_when_not_following_raises_not_found(self, create_user):
        amina = create_user(username="amina")
        brian = create_user(username="brian")
        with pytest.raises(NotFoundError):
            user_service.unfollow_user(amina, brian.id)


class TestListUsers:
    def test_filters_by_role(self, create_user):
        create_user(username="farmerx", role="farmer")
        create_user(username="expertx", role="expert")

        results = user_service.list_users(role="expert")

        assert [u.username for u in results] == ["expertx"]

    def test_no_filters_returns_everyone(self, create_user):
        create_user(username="amina")
        create_user(username="brian")

        results = user_service.list_users()

        assert {u.username for u in results} == {"amina", "brian"}

    def test_search_matches_username_case_insensitively(self, create_user):
        create_user(username="Amina")
        create_user(username="brian")

        results = user_service.list_users(search="amin")

        assert [u.username for u in results] == ["Amina"]


class TestListFollowingIds:
    def test_returns_ids_of_followed_users(self, create_user):
        amina = create_user(username="amina")
        brian = create_user(username="brian")
        user_service.follow_user(amina, brian.id)

        assert user_service.list_following_ids(amina) == [brian.id]

    def test_empty_when_following_no_one(self, create_user):
        amina = create_user(username="amina")
        assert user_service.list_following_ids(amina) == []


class TestCountFollowers:
    def test_counts_followers(self, create_user):
        amina = create_user(username="amina")
        brian = create_user(username="brian")
        user_service.follow_user(brian, amina.id)

        assert user_service.count_followers(amina.id) == 1

    def test_zero_for_unfollowed_user(self, create_user):
        amina = create_user(username="amina")
        assert user_service.count_followers(amina.id) == 0

    def test_raises_not_found_for_missing_user(self):
        with pytest.raises(NotFoundError):
            user_service.count_followers(999999)

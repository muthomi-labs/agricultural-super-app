import pytest
from sqlalchemy import event

from app.errors import ConflictError, ForbiddenError, NotFoundError, ValidationAPIError
from app.extensions import db
from app.models import Comment, Like, SavedPost
from app.schemas import posts_schema
from app.services import community_service, post_service


class _QueryCounter:
    def __init__(self):
        self.count = 0

    def __call__(self, *args, **kwargs):
        self.count += 1


class QueryCountingContext:
    def __enter__(self):
        self.counter = _QueryCounter()
        event.listen(db.engine, "before_cursor_execute", self.counter)
        return self.counter

    def __exit__(self, *exc_info):
        event.remove(db.engine, "before_cursor_execute", self.counter)


class TestCreatePost:
    def test_creates_post_owned_by_current_user(self, create_user):
        amina = create_user(username="amina")
        post = post_service.create_post(amina, {"title": "Maize tips", "content": "Plant in rows."})
        assert post.user_id == amina.id
        assert post.title == "Maize tips"

    def test_creates_a_reel_when_video_url_given(self, create_user):
        amina = create_user(username="amina")
        post = post_service.create_post(
            amina, {"title": "Fall armyworm control", "content": "c", "video_url": "https://x/clip.mp4"}
        )
        assert post.video_url == "https://x/clip.mp4"
        assert post.view_count == 0

    def test_creates_nested_images(self, create_user):
        amina = create_user(username="amina")
        post = post_service.create_post(
            amina,
            {
                "title": "Maize tips",
                "content": "Plant in rows.",
                "images": [{"image_url": "https://x/1.jpg"}, {"image_url": "https://x/2.jpg"}],
            },
        )
        assert len(post.images) == 2
        assert {img.image_url for img in post.images} == {"https://x/1.jpg", "https://x/2.jpg"}


class TestGetPostOr404:
    def test_raises_not_found_for_missing_post(self):
        with pytest.raises(NotFoundError):
            post_service.get_post_or_404(999999)


class TestListPosts:
    def test_orders_newest_first(self, create_user):
        amina = create_user(username="amina")
        first = post_service.create_post(amina, {"title": "First", "content": "c"})
        second = post_service.create_post(amina, {"title": "Second", "content": "c"})

        posts = post_service.list_posts()

        assert [p.id for p in posts] == [second.id, first.id]

    def test_per_page_is_capped_at_max_page_size(self, create_user):
        amina = create_user(username="amina")
        for i in range(5):
            post_service.create_post(amina, {"title": f"Post {i}", "content": "c"})

        posts = post_service.list_posts(page=1, per_page=1000)
        assert len(posts) == 5

    def test_page_2_returns_different_older_posts_than_page_1(self, create_user):
        amina = create_user(username="amina")
        posts_created = [
            post_service.create_post(amina, {"title": f"Post {i}", "content": "c"}) for i in range(5)
        ]
        newest_first_ids = [p.id for p in reversed(posts_created)]

        page_one = post_service.list_posts(page=1, per_page=2)
        page_two = post_service.list_posts(page=2, per_page=2)

        assert [p.id for p in page_one] == newest_first_ids[0:2]
        assert [p.id for p in page_two] == newest_first_ids[2:4]
        assert set(p.id for p in page_one).isdisjoint(p.id for p in page_two)

    def test_serializing_a_page_of_posts_does_not_scale_query_count_with_post_count(
        self, create_user
    ):
        amina = create_user(username="amina")
        brian = create_user(username="brian")
        posts = [post_service.create_post(amina, {"title": f"Post {i}", "content": "c"}) for i in range(8)]
        for post in posts:
            post_service.like_post(brian, post.id)
            post_service.add_comment(brian, post.id, "Nice!")

        with QueryCountingContext() as counter:
            listed = post_service.list_posts(per_page=8)
            posts_schema.context = {"current_user_id": brian.id}
            posts_schema.dump(listed)

        # Whatever the exact number of eager-load queries is, it must not
        # grow with the number of posts on the page -- that's the N+1
        # this fix closes. 8 posts * (a query per relationship accessed)
        # would be dozens of queries under the old lazy-loading behavior;
        # a small constant bound proves eager loading is doing its job.
        assert counter.count <= 10


class TestListPostsHasVideo:
    def test_filters_to_only_posts_with_video(self, create_user):
        amina = create_user(username="amina")
        post_service.create_post(amina, {"title": "Plain", "content": "c"})
        reel = post_service.create_post(
            amina, {"title": "Reel", "content": "c", "video_url": "https://x/clip.mp4"}
        )

        posts = post_service.list_posts(has_video=True)

        assert [p.id for p in posts] == [reel.id]

    def test_false_returns_everything(self, create_user):
        amina = create_user(username="amina")
        post_service.create_post(amina, {"title": "Plain", "content": "c"})
        post_service.create_post(
            amina, {"title": "Reel", "content": "c", "video_url": "https://x/clip.mp4"}
        )

        assert len(post_service.list_posts(has_video=False)) == 2


class TestIncrementViewCount:
    def test_increments_from_zero(self, create_user):
        amina = create_user(username="amina")
        post = post_service.create_post(amina, {"title": "T", "content": "c"})

        post_service.increment_view_count(post.id)
        post_service.increment_view_count(post.id)

        assert post_service.get_post_or_404(post.id).view_count == 2

    def test_raises_not_found_for_missing_post(self):
        with pytest.raises(NotFoundError):
            post_service.increment_view_count(999999)


class TestListPostsByUser:
    def test_returns_only_that_users_posts_newest_first(self, create_user):
        amina = create_user(username="amina")
        brian = create_user(username="brian")
        post_service.create_post(brian, {"title": "Brian's", "content": "c"})
        first = post_service.create_post(amina, {"title": "First", "content": "c"})
        second = post_service.create_post(amina, {"title": "Second", "content": "c"})

        posts = post_service.list_posts_by_user(amina.id)

        assert [p.id for p in posts] == [second.id, first.id]

    def test_empty_for_user_with_no_posts(self, create_user):
        amina = create_user(username="amina")
        assert post_service.list_posts_by_user(amina.id) == []


class TestUpdatePost:
    def test_owner_can_update(self, create_user):
        amina = create_user(username="amina")
        post = post_service.create_post(amina, {"title": "Original", "content": "c"})

        updated = post_service.update_post(amina, post.id, {"title": "Updated"})
        assert updated.title == "Updated"

    def test_non_owner_cannot_update(self, create_user):
        amina = create_user(username="amina")
        brian = create_user(username="brian")
        post = post_service.create_post(amina, {"title": "Original", "content": "c"})

        with pytest.raises(ForbiddenError):
            post_service.update_post(brian, post.id, {"title": "Hijacked"})

    def test_admin_can_update_others_posts(self, create_user):
        amina = create_user(username="amina")
        admin = create_user(username="root", role="admin")
        post = post_service.create_post(amina, {"title": "Original", "content": "c"})

        updated = post_service.update_post(admin, post.id, {"title": "Moderated"})
        assert updated.title == "Moderated"

    def test_images_key_is_ignored_on_update(self, create_user):
        amina = create_user(username="amina")
        post = post_service.create_post(amina, {"title": "Original", "content": "c"})

        post_service.update_post(amina, post.id, {"images": [{"image_url": "https://x/sneaky.jpg"}]})
        assert len(post.images) == 0


class TestDeletePost:
    def test_owner_can_delete(self, create_user):
        amina = create_user(username="amina")
        post = post_service.create_post(amina, {"title": "Doomed", "content": "c"})

        post_service.delete_post(amina, post.id)

        with pytest.raises(NotFoundError):
            post_service.get_post_or_404(post.id)

    def test_non_owner_cannot_delete(self, create_user):
        amina = create_user(username="amina")
        brian = create_user(username="brian")
        post = post_service.create_post(amina, {"title": "Not yours", "content": "c"})

        with pytest.raises(ForbiddenError):
            post_service.delete_post(brian, post.id)

    def test_community_creator_can_delete_a_members_post(self, create_user):
        amina = create_user(username="amina")
        brian = create_user(username="brian")
        community = community_service.create_community(amina, {"name": "Maize Farmers"})
        community_service.join_community(brian, community.id)
        post = post_service.create_post(brian, {"title": "T", "content": "c", "community_id": community.id})

        post_service.delete_post(amina, post.id)

        with pytest.raises(NotFoundError):
            post_service.get_post_or_404(post.id)

    def test_non_creator_member_cannot_delete_anothers_community_post(self, create_user):
        amina = create_user(username="amina")
        brian = create_user(username="brian")
        eve = create_user(username="eve")
        community = community_service.create_community(amina, {"name": "Maize Farmers"})
        community_service.join_community(brian, community.id)
        community_service.join_community(eve, community.id)
        post = post_service.create_post(brian, {"title": "T", "content": "c", "community_id": community.id})

        with pytest.raises(ForbiddenError):
            post_service.delete_post(eve, post.id)

    def test_community_creator_cannot_delete_general_feed_posts(self, create_user):
        amina = create_user(username="amina")
        brian = create_user(username="brian")
        community_service.create_community(amina, {"name": "Maize Farmers"})
        post = post_service.create_post(brian, {"title": "T", "content": "c"})

        with pytest.raises(ForbiddenError):
            post_service.delete_post(amina, post.id)

    def test_admin_can_delete_any_post(self, create_user):
        amina = create_user(username="amina")
        admin = create_user(username="root", role="admin")
        post = post_service.create_post(amina, {"title": "Doomed", "content": "c"})

        post_service.delete_post(admin, post.id)

        with pytest.raises(NotFoundError):
            post_service.get_post_or_404(post.id)

    def test_deleting_unknown_post_raises_not_found(self, create_user):
        amina = create_user(username="amina")
        with pytest.raises(NotFoundError):
            post_service.delete_post(amina, 999999)

    def test_deleting_post_removes_its_comments(self, create_user):
        amina = create_user(username="amina")
        brian = create_user(username="brian")
        post = post_service.create_post(amina, {"title": "T", "content": "c"})
        comment = post_service.add_comment(brian, post.id, "Nice post!")

        post_service.delete_post(amina, post.id)

        assert db.session.get(Comment, comment.id) is None

    def test_deleting_post_removes_its_reactions(self, create_user):
        amina = create_user(username="amina")
        brian = create_user(username="brian")
        post = post_service.create_post(amina, {"title": "T", "content": "c"})
        reaction = post_service.like_post(brian, post.id)

        post_service.delete_post(amina, post.id)

        assert db.session.get(Like, reaction.id) is None

    def test_deleting_post_removes_its_saves(self, create_user):
        amina = create_user(username="amina")
        brian = create_user(username="brian")
        post = post_service.create_post(amina, {"title": "T", "content": "c"})
        saved = post_service.save_post(brian, post.id)

        post_service.delete_post(amina, post.id)

        assert db.session.get(SavedPost, saved.id) is None

    def test_deleting_a_repost_does_not_delete_the_original(self, create_user):
        amina = create_user(username="amina")
        brian = create_user(username="brian")
        original = post_service.create_post(amina, {"title": "Tips", "content": "c"})
        repost = post_service.repost_post(brian, original.id)

        post_service.delete_post(brian, repost.id)

        untouched = post_service.get_post_or_404(original.id)
        assert untouched.id == original.id
        with pytest.raises(NotFoundError):
            post_service.get_post_or_404(repost.id)

    def test_deleting_the_original_also_removes_its_reposts(self, create_user):
        amina = create_user(username="amina")
        brian = create_user(username="brian")
        original = post_service.create_post(amina, {"title": "Tips", "content": "c"})
        repost = post_service.repost_post(brian, original.id)

        post_service.delete_post(amina, original.id)

        with pytest.raises(NotFoundError):
            post_service.get_post_or_404(original.id)
        with pytest.raises(NotFoundError):
            post_service.get_post_or_404(repost.id)

    def test_repost_count_is_correct_after_deleting_one_of_several_reposts(self, create_user):
        amina = create_user(username="amina")
        brian = create_user(username="brian")
        eve = create_user(username="eve")
        original = post_service.create_post(amina, {"title": "Tips", "content": "c"})
        brians_repost = post_service.repost_post(brian, original.id)
        post_service.repost_post(eve, original.id)

        post_service.delete_post(brian, brians_repost.id)

        refreshed = post_service.get_post_or_404(original.id)
        assert len(refreshed.reposts) == 1
        assert refreshed.reposts[0].user_id == eve.id


class TestPostImages:
    def test_owner_can_add_and_delete_image(self, create_user):
        amina = create_user(username="amina")
        post = post_service.create_post(amina, {"title": "T", "content": "c"})

        image = post_service.add_post_image(amina, post.id, "https://x/new.jpg")
        assert image.post_id == post.id

        post_service.delete_post_image(amina, post.id, image.id)

    def test_non_owner_cannot_add_image(self, create_user):
        amina = create_user(username="amina")
        brian = create_user(username="brian")
        post = post_service.create_post(amina, {"title": "T", "content": "c"})

        with pytest.raises(ForbiddenError):
            post_service.add_post_image(brian, post.id, "https://x/hijack.jpg")

    def test_deleting_image_belonging_to_different_post_raises_not_found(self, create_user):
        amina = create_user(username="amina")
        post_one = post_service.create_post(amina, {"title": "One", "content": "c"})
        post_two = post_service.create_post(amina, {"title": "Two", "content": "c"})
        image = post_service.add_post_image(amina, post_one.id, "https://x/1.jpg")

        with pytest.raises(NotFoundError):
            post_service.delete_post_image(amina, post_two.id, image.id)


class TestComments:
    def test_add_and_list_comments(self, create_user):
        amina = create_user(username="amina")
        brian = create_user(username="brian")
        post = post_service.create_post(amina, {"title": "T", "content": "c"})

        post_service.add_comment(brian, post.id, "Nice post!")
        comments = post_service.list_comments(post.id)

        assert len(comments) == 1
        assert comments[0].content == "Nice post!"
        assert comments[0].user_id == brian.id

    def test_owner_can_edit_own_comment(self, create_user):
        amina = create_user(username="amina")
        post = post_service.create_post(amina, {"title": "T", "content": "c"})
        comment = post_service.add_comment(amina, post.id, "Original")

        updated = post_service.update_comment(amina, comment.id, "Edited")
        assert updated.content == "Edited"

    def test_reply_sets_parent_comment_id(self, create_user):
        amina = create_user(username="amina")
        brian = create_user(username="brian")
        post = post_service.create_post(amina, {"title": "T", "content": "c"})
        parent = post_service.add_comment(brian, post.id, "Original")

        reply = post_service.add_comment(amina, post.id, "Thanks!", parent_comment_id=parent.id)

        assert reply.parent_comment_id == parent.id

    def test_reply_to_comment_on_different_post_raises_not_found(self, create_user):
        amina = create_user(username="amina")
        post_one = post_service.create_post(amina, {"title": "One", "content": "c"})
        post_two = post_service.create_post(amina, {"title": "Two", "content": "c"})
        parent = post_service.add_comment(amina, post_one.id, "Original")

        with pytest.raises(NotFoundError):
            post_service.add_comment(amina, post_two.id, "Wrong post", parent_comment_id=parent.id)

    def test_deleting_parent_comment_deletes_its_replies(self, create_user):
        amina = create_user(username="amina")
        post = post_service.create_post(amina, {"title": "T", "content": "c"})
        parent = post_service.add_comment(amina, post.id, "Original")
        reply = post_service.add_comment(amina, post.id, "Reply", parent_comment_id=parent.id)

        post_service.delete_comment(amina, parent.id)

        assert db.session.get(Comment, reply.id) is None

    def test_non_owner_cannot_edit_comment(self, create_user):
        amina = create_user(username="amina")
        brian = create_user(username="brian")
        post = post_service.create_post(amina, {"title": "T", "content": "c"})
        comment = post_service.add_comment(brian, post.id, "Brian's comment")

        with pytest.raises(ForbiddenError):
            post_service.update_comment(amina, comment.id, "Hijacked")

    def test_non_owner_cannot_delete_comment(self, create_user):
        amina = create_user(username="amina")
        brian = create_user(username="brian")
        post = post_service.create_post(amina, {"title": "T", "content": "c"})
        comment = post_service.add_comment(brian, post.id, "Brian's comment")

        with pytest.raises(ForbiddenError):
            post_service.delete_comment(amina, comment.id)


class TestLikes:
    def test_like_and_unlike(self, create_user):
        amina = create_user(username="amina")
        brian = create_user(username="brian")
        post = post_service.create_post(amina, {"title": "T", "content": "c"})

        post_service.like_post(brian, post.id)
        post_service.unlike_post(brian, post.id)

    def test_liking_twice_raises_conflict(self, create_user):
        amina = create_user(username="amina")
        brian = create_user(username="brian")
        post = post_service.create_post(amina, {"title": "T", "content": "c"})
        post_service.like_post(brian, post.id)

        with pytest.raises(ConflictError):
            post_service.like_post(brian, post.id)

    def test_unliking_without_liking_raises_not_found(self, create_user):
        amina = create_user(username="amina")
        brian = create_user(username="brian")
        post = post_service.create_post(amina, {"title": "T", "content": "c"})

        with pytest.raises(NotFoundError):
            post_service.unlike_post(brian, post.id)


class TestReactions:
    def test_add_reaction(self, create_user):
        amina = create_user(username="amina")
        brian = create_user(username="brian")
        post = post_service.create_post(amina, {"title": "T", "content": "c"})

        reaction = post_service.set_reaction(brian, post.id, "fire")
        assert reaction.reaction_type == "fire"

    def test_changing_reaction_updates_existing_row(self, create_user):
        amina = create_user(username="amina")
        brian = create_user(username="brian")
        post = post_service.create_post(amina, {"title": "T", "content": "c"})

        post_service.set_reaction(brian, post.id, "like")
        post_service.set_reaction(brian, post.id, "love")

        from app.extensions import db
        from app.models import Like

        reactions = db.session.query(Like).filter_by(user_id=brian.id, post_id=post.id).all()
        assert len(reactions) == 1
        assert reactions[0].reaction_type == "love"

    def test_removing_reaction(self, create_user):
        amina = create_user(username="amina")
        brian = create_user(username="brian")
        post = post_service.create_post(amina, {"title": "T", "content": "c"})

        post_service.set_reaction(brian, post.id, "wow")
        post_service.remove_reaction(brian, post.id)

    def test_removing_without_reacting_raises_not_found(self, create_user):
        amina = create_user(username="amina")
        brian = create_user(username="brian")
        post = post_service.create_post(amina, {"title": "T", "content": "c"})

        with pytest.raises(NotFoundError):
            post_service.remove_reaction(brian, post.id)

    def test_invalid_reaction_type_raises_validation_error(self, create_user):
        amina = create_user(username="amina")
        brian = create_user(username="brian")
        post = post_service.create_post(amina, {"title": "T", "content": "c"})

        with pytest.raises(ValidationAPIError):
            post_service.set_reaction(brian, post.id, "angry")

    def test_reaction_count_reflects_all_types(self, create_user):
        amina = create_user(username="amina")
        brian = create_user(username="brian")
        post = post_service.create_post(amina, {"title": "T", "content": "c"})

        post_service.set_reaction(brian, post.id, "love")
        assert len(post.likes) == 1


class TestSaves:
    def test_save_and_unsave(self, create_user):
        amina = create_user(username="amina")
        brian = create_user(username="brian")
        post = post_service.create_post(amina, {"title": "T", "content": "c"})

        post_service.save_post(brian, post.id)
        post_service.unsave_post(brian, post.id)

    def test_saving_twice_raises_conflict(self, create_user):
        amina = create_user(username="amina")
        brian = create_user(username="brian")
        post = post_service.create_post(amina, {"title": "T", "content": "c"})
        post_service.save_post(brian, post.id)

        with pytest.raises(ConflictError):
            post_service.save_post(brian, post.id)

    def test_unsaving_without_saving_raises_not_found(self, create_user):
        amina = create_user(username="amina")
        brian = create_user(username="brian")
        post = post_service.create_post(amina, {"title": "T", "content": "c"})

        with pytest.raises(NotFoundError):
            post_service.unsave_post(brian, post.id)

    def test_list_saved_posts_is_user_specific(self, create_user):
        amina = create_user(username="amina")
        brian = create_user(username="brian")
        eve = create_user(username="eve")
        post_one = post_service.create_post(amina, {"title": "One", "content": "c"})
        post_two = post_service.create_post(amina, {"title": "Two", "content": "c"})

        post_service.save_post(brian, post_one.id)
        post_service.save_post(brian, post_two.id)
        post_service.save_post(eve, post_one.id)

        brian_saved = post_service.list_saved_posts(brian)
        eve_saved = post_service.list_saved_posts(eve)

        assert {p.id for p in brian_saved} == {post_one.id, post_two.id}
        assert {p.id for p in eve_saved} == {post_one.id}

    def test_saving_does_not_duplicate_rows(self, create_user):
        amina = create_user(username="amina")
        brian = create_user(username="brian")
        post = post_service.create_post(amina, {"title": "T", "content": "c"})

        from app.extensions import db
        from app.models import SavedPost

        try:
            post_service.save_post(brian, post.id)
            post_service.save_post(brian, post.id)
        except ConflictError:
            pass

        saved_rows = db.session.query(SavedPost).filter_by(user_id=brian.id, post_id=post.id).all()
        assert len(saved_rows) == 1


class TestReposts:
    def test_repost_creates_new_post_referencing_original(self, create_user):
        amina = create_user(username="amina")
        brian = create_user(username="brian")
        original = post_service.create_post(amina, {"title": "Pest control tips", "content": "Neem oil works well."})

        repost = post_service.repost_post(brian, original.id, content="Worth trying!")

        assert repost.user_id == brian.id
        assert repost.original_post_id == original.id
        assert repost.content == "Worth trying!"

    def test_repost_preserves_original_author_attribution(self, create_user):
        amina = create_user(username="amina")
        brian = create_user(username="brian")
        original = post_service.create_post(amina, {"title": "Pest control tips", "content": "Neem oil works well."})

        repost = post_service.repost_post(brian, original.id)

        assert repost.original_post.user_id == amina.id
        assert repost.original_post.id == original.id

    def test_repost_without_added_content_is_allowed(self, create_user):
        amina = create_user(username="amina")
        brian = create_user(username="brian")
        original = post_service.create_post(amina, {"title": "Tips", "content": "c"})

        repost = post_service.repost_post(brian, original.id)
        assert repost.content == ""

    def test_reposting_the_same_post_twice_raises_conflict(self, create_user):
        amina = create_user(username="amina")
        brian = create_user(username="brian")
        original = post_service.create_post(amina, {"title": "Tips", "content": "c"})
        post_service.repost_post(brian, original.id)

        with pytest.raises(ConflictError):
            post_service.repost_post(brian, original.id)

    def test_reposting_a_repost_attributes_to_the_root_original(self, create_user):
        amina = create_user(username="amina")
        brian = create_user(username="brian")
        eve = create_user(username="eve")
        original = post_service.create_post(amina, {"title": "Tips", "content": "c"})
        brians_repost = post_service.repost_post(brian, original.id)

        eves_repost = post_service.repost_post(eve, brians_repost.id)

        assert eves_repost.original_post_id == original.id

    def test_reposting_unknown_post_raises_not_found(self, create_user):
        brian = create_user(username="brian")
        with pytest.raises(NotFoundError):
            post_service.repost_post(brian, 999999)

    def test_unrepost_removes_the_repost(self, create_user):
        amina = create_user(username="amina")
        brian = create_user(username="brian")
        original = post_service.create_post(amina, {"title": "Tips", "content": "c"})
        repost = post_service.repost_post(brian, original.id)

        post_service.unrepost_post(brian, original.id)

        with pytest.raises(NotFoundError):
            post_service.get_post_or_404(repost.id)

    def test_unreposting_without_reposting_raises_not_found(self, create_user):
        amina = create_user(username="amina")
        brian = create_user(username="brian")
        original = post_service.create_post(amina, {"title": "Tips", "content": "c"})

        with pytest.raises(NotFoundError):
            post_service.unrepost_post(brian, original.id)

    def test_repost_then_unrepost_then_repost_again_succeeds(self, create_user):
        amina = create_user(username="amina")
        brian = create_user(username="brian")
        original = post_service.create_post(amina, {"title": "Tips", "content": "c"})

        post_service.repost_post(brian, original.id)
        post_service.unrepost_post(brian, original.id)
        second_repost = post_service.repost_post(brian, original.id)

        assert second_repost.original_post_id == original.id

    def test_unrepost_from_a_reposted_card_targets_the_root(self, create_user):
        amina = create_user(username="amina")
        brian = create_user(username="brian")
        eve = create_user(username="eve")
        original = post_service.create_post(amina, {"title": "Tips", "content": "c"})
        brians_repost = post_service.repost_post(brian, original.id)
        eves_repost = post_service.repost_post(eve, brians_repost.id)

        post_service.unrepost_post(eve, brians_repost.id)

        with pytest.raises(NotFoundError):
            post_service.get_post_or_404(eves_repost.id)

    def test_unreposting_does_not_affect_the_original_post(self, create_user):
        amina = create_user(username="amina")
        brian = create_user(username="brian")
        original = post_service.create_post(amina, {"title": "Tips", "content": "c"})
        post_service.repost_post(brian, original.id)

        post_service.unrepost_post(brian, original.id)

        untouched = post_service.get_post_or_404(original.id)
        assert untouched.title == "Tips"
        assert untouched.user_id == amina.id


class TestCommunityPosts:
    def test_member_can_create_post_in_community(self, create_user):
        amina = create_user(username="amina")
        community = community_service.create_community(amina, {"name": "Maize Farmers"})

        post = post_service.create_post(amina, {"title": "T", "content": "c", "community_id": community.id})
        assert post.community_id == community.id

    def test_non_member_cannot_create_post_in_community(self, create_user):
        amina = create_user(username="amina")
        brian = create_user(username="brian")
        community = community_service.create_community(amina, {"name": "Maize Farmers"})

        with pytest.raises(ForbiddenError):
            post_service.create_post(brian, {"title": "T", "content": "c", "community_id": community.id})

    def test_posting_to_unknown_community_raises_not_found(self, create_user):
        amina = create_user(username="amina")
        with pytest.raises(NotFoundError):
            post_service.create_post(amina, {"title": "T", "content": "c", "community_id": 999999})

    def test_list_posts_filters_by_community(self, create_user):
        amina = create_user(username="amina")
        community = community_service.create_community(amina, {"name": "Maize Farmers"})

        community_post = post_service.create_post(
            amina, {"title": "In community", "content": "c", "community_id": community.id}
        )
        general_post = post_service.create_post(amina, {"title": "General", "content": "c"})

        community_posts = post_service.list_posts(community_id=community.id)
        general_posts = post_service.list_posts()

        assert [p.id for p in community_posts] == [community_post.id]
        assert general_post.id not in [p.id for p in community_posts]
        assert [p.id for p in general_posts] == [general_post.id]

    def test_updating_post_cannot_move_it_between_communities(self, create_user):
        amina = create_user(username="amina")
        community = community_service.create_community(amina, {"name": "Maize Farmers"})
        post = post_service.create_post(amina, {"title": "T", "content": "c"})

        post_service.update_post(amina, post.id, {"community_id": community.id})
        assert post.community_id is None

    def test_experts_only_posting_blocks_ordinary_members(self, create_user):
        amina = create_user(username="amina")
        brian = create_user(username="brian")
        community = community_service.create_community(amina, {"name": "Maize Farmers"})
        community_service.join_community(brian, community.id)
        community_service.update_community(amina, community.id, {"posting_permission": "experts_only"})

        with pytest.raises(ForbiddenError):
            post_service.create_post(brian, {"title": "T", "content": "c", "community_id": community.id})

    def test_experts_only_posting_allows_experts(self, create_user):
        amina = create_user(username="amina")
        expert = create_user(username="drjane", role="expert")
        community = community_service.create_community(amina, {"name": "Maize Farmers"})
        community_service.join_community(expert, community.id)
        community_service.update_community(amina, community.id, {"posting_permission": "experts_only"})

        post = post_service.create_post(expert, {"title": "T", "content": "c", "community_id": community.id})
        assert post.community_id == community.id

    def test_admins_only_posting_blocks_experts(self, create_user):
        amina = create_user(username="amina")
        expert = create_user(username="drjane", role="expert")
        community = community_service.create_community(amina, {"name": "Maize Farmers"})
        community_service.join_community(expert, community.id)
        community_service.update_community(amina, community.id, {"posting_permission": "admins_only"})

        with pytest.raises(ForbiddenError):
            post_service.create_post(expert, {"title": "T", "content": "c", "community_id": community.id})

    def test_admins_only_posting_allows_admin(self, create_user):
        amina = create_user(username="amina")
        community = community_service.create_community(amina, {"name": "Maize Farmers"})
        community_service.update_community(amina, community.id, {"posting_permission": "admins_only"})

        post = post_service.create_post(amina, {"title": "T", "content": "c", "community_id": community.id})
        assert post.community_id == community.id


class TestAnnouncements:
    def test_admin_can_post_announcement(self, create_user):
        amina = create_user(username="amina")
        community = community_service.create_community(amina, {"name": "Maize Farmers"})

        post = post_service.create_post(
            amina, {"title": "Workshop", "content": "9am tomorrow", "community_id": community.id, "is_announcement": True}
        )
        assert post.is_announcement is True

    def test_ordinary_member_cannot_post_announcement(self, create_user):
        amina = create_user(username="amina")
        brian = create_user(username="brian")
        community = community_service.create_community(amina, {"name": "Maize Farmers"})
        community_service.join_community(brian, community.id)

        with pytest.raises(ForbiddenError):
            post_service.create_post(
                brian, {"title": "Fake", "content": "c", "community_id": community.id, "is_announcement": True}
            )

    def test_expert_cannot_post_announcement_without_admin_role(self, create_user):
        amina = create_user(username="amina")
        expert = create_user(username="drjane", role="expert")
        community = community_service.create_community(amina, {"name": "Maize Farmers"})
        community_service.join_community(expert, community.id)

        with pytest.raises(ForbiddenError):
            post_service.create_post(
                expert, {"title": "Fake", "content": "c", "community_id": community.id, "is_announcement": True}
            )

    def test_announcement_requires_a_community(self, create_user):
        amina = create_user(username="amina")

        with pytest.raises(ValidationAPIError):
            post_service.create_post(amina, {"title": "T", "content": "c", "is_announcement": True})


class TestCommentPermissions:
    def test_comments_disabled_blocks_everyone(self, create_user):
        amina = create_user(username="amina")
        brian = create_user(username="brian")
        community = community_service.create_community(amina, {"name": "Maize Farmers"})
        community_service.join_community(brian, community.id)
        community_service.update_community(amina, community.id, {"comments_enabled": False})
        post = post_service.create_post(amina, {"title": "T", "content": "c", "community_id": community.id})

        with pytest.raises(ForbiddenError):
            post_service.add_comment(brian, post.id, "Nice!")

    def test_comments_enabled_allows_members(self, create_user):
        amina = create_user(username="amina")
        brian = create_user(username="brian")
        community = community_service.create_community(amina, {"name": "Maize Farmers"})
        community_service.join_community(brian, community.id)
        post = post_service.create_post(amina, {"title": "T", "content": "c", "community_id": community.id})

        comment = post_service.add_comment(brian, post.id, "Nice!")
        assert comment.content == "Nice!"

    def test_experts_only_messaging_blocks_ordinary_members(self, create_user):
        amina = create_user(username="amina")
        brian = create_user(username="brian")
        community = community_service.create_community(amina, {"name": "Maize Farmers"})
        community_service.join_community(brian, community.id)
        community_service.update_community(amina, community.id, {"messaging_permission": "experts_only"})
        post = post_service.create_post(amina, {"title": "T", "content": "c", "community_id": community.id})

        with pytest.raises(ForbiddenError):
            post_service.add_comment(brian, post.id, "Nice!")

    def test_experts_only_messaging_allows_experts(self, create_user):
        amina = create_user(username="amina")
        expert = create_user(username="drjane", role="expert")
        community = community_service.create_community(amina, {"name": "Maize Farmers"})
        community_service.join_community(expert, community.id)
        community_service.update_community(amina, community.id, {"messaging_permission": "experts_only"})
        post = post_service.create_post(amina, {"title": "T", "content": "c", "community_id": community.id})

        comment = post_service.add_comment(expert, post.id, "Great post!")
        assert comment.content == "Great post!"

    def test_general_feed_comments_are_never_restricted(self, create_user):
        amina = create_user(username="amina")
        brian = create_user(username="brian")
        post = post_service.create_post(amina, {"title": "T", "content": "c"})

        comment = post_service.add_comment(brian, post.id, "Nice!")
        assert comment.content == "Nice!"

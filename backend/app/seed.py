import json
from datetime import datetime, date, timezone, timedelta
from app.database import SessionLocal, Base, engine
from app.models.user import User, Workspace, WorkspaceMember
from app.models.instagram import InstagramAccount
from app.models.automation import Automation, AutomationLog
from app.models.profile import CreatorProfile
from app.models.campaign import BrandCampaign, CampaignApplication
from app.models.invoice import Invoice
from app.models.subscription import Subscription
from app.models.notification import Notification
from app.security import get_password_hash, encrypt_token

def seed_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        print("Checking and seeding Woka database...")

        # 1. Creator User (Alex Rivera)
        creator = db.query(User).filter(User.email == "creator@woka.io").first()
        if not creator:
            creator = User(
                email="creator@woka.io",
                hashed_password=get_password_hash("Creator123!"),
                full_name="Alex Rivera",
                role="CREATOR",
                avatar_url="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80",
                is_active=True,
                is_verified=True
            )
            db.add(creator)
            db.flush()

            creator_ws = Workspace(name="Alex Rivera Studio", owner_id=creator.id)
            db.add(creator_ws)
            db.flush()

            db.add(WorkspaceMember(workspace_id=creator_ws.id, user_id=creator.id, role_in_workspace="OWNER"))

            # Subscription: Pro
            db.add(Subscription(
                workspace_id=creator_ws.id,
                plan_tier="PRO",
                status="ACTIVE",
                dm_limit_monthly=2000,
                dm_used_monthly=142,
                ai_limit_monthly=500,
                ai_used_monthly=38
            ))

            # Instagram Account (Sandbox)
            ig_account = InstagramAccount(
                workspace_id=creator_ws.id,
                ig_user_id="ig_demo_alex_rivera",
                username="alex_creativestudio",
                name="Alex Rivera | Creator & Tech",
                profile_pic_url="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80",
                encrypted_access_token=encrypt_token("sandbox_access_token_demo_valid"),
                token_expires_at=datetime.now(timezone.utc) + timedelta(days=58),
                is_connected=True,
                is_sandbox=True,
                followers_count=48500,
                media_count=142
            )
            db.add(ig_account)
            db.flush()

            # Creator Profile / Public Media Kit
            db.add(CreatorProfile(
                workspace_id=creator_ws.id,
                slug="alexrivera",
                display_name="Alex Rivera",
                bio="Tech & Creator Economy educator helping 48k+ creators monetize attention and build scalable media workflows.",
                avatar_url="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=200&auto=format&fit=crop&q=80",
                niches=json.dumps(["Tech", "Productivity", "Creator Economy", "SaaS"]),
                location="San Francisco, CA",
                rate_reel=450.0,
                rate_story=150.0,
                rate_bundle=550.0,
                is_verified=True,
                is_public=True
            ))

            # Automations
            auto1 = Automation(
                workspace_id=creator_ws.id,
                ig_account_id=ig_account.id,
                name="Free 2026 Creator Toolkit Guide",
                trigger_type="COMMENT",
                target_post_type="ALL_POSTS",
                match_type="CONTAINS_ANY",
                trigger_keywords=json.dumps(["toolkit", "guide", "free", "tools"]),
                dm_message_template="Hey {{username}}! Thanks for commenting. Here is the direct link to download the 2026 Creator Toolkit: https://woka.io/resources/toolkit2026 Enjoy!",
                reply_comment_template="Just sent the guide to your DMs {{username}}! Check your message requests 🚀",
                is_active=True,
                cooldown_minutes=60,
                total_triggered_count=89
            )
            db.add(auto1)
            db.flush()

            auto2 = Automation(
                workspace_id=creator_ws.id,
                ig_account_id=ig_account.id,
                name="Brand Pitch Template Vault",
                trigger_type="COMMENT",
                target_post_type="SPECIFIC_POST",
                target_post_id="post_top_2",
                target_post_preview_url="https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=200&auto=format&fit=crop&q=80",
                match_type="CONTAINS_ANY",
                trigger_keywords=json.dumps(["pitch", "template", "vault", "rate"]),
                dm_message_template="Hey {{username}}! Here are the 5 email pitch templates that landed me $15k in sponsorships: https://woka.io/pitch-vault Let me know what you think!",
                reply_comment_template="Sent you the pitch templates in your DMs {{username}}! 💌",
                is_active=True,
                cooldown_minutes=120,
                total_triggered_count=53
            )
            db.add(auto2)
            db.flush()

            # Seed Execution Logs
            db.add(AutomationLog(
                automation_id=auto1.id,
                recipient_ig_id="ig_fan_sarah",
                recipient_username="sarah_designs",
                trigger_comment_id="c_101",
                trigger_comment_text="Could you please share the toolkit link?",
                dm_text_sent="Hey @sarah_designs! Thanks for commenting. Here is the direct link to download...",
                status="SUCCESS",
                created_at=datetime.now(timezone.utc) - timedelta(minutes=14)
            ))
            db.add(AutomationLog(
                automation_id=auto1.id,
                recipient_ig_id="ig_fan_jordan",
                recipient_username="jordan_builds",
                trigger_comment_id="c_102",
                trigger_comment_text="Need the guide! Loving this series.",
                dm_text_sent="Hey @jordan_builds! Thanks for commenting. Here is the direct link to download...",
                status="SUCCESS",
                created_at=datetime.now(timezone.utc) - timedelta(hours=2)
            ))

            # Invoices for Alex
            db.add(Invoice(
                workspace_id=creator_ws.id,
                invoice_number="INV-2026-001",
                client_name="Lumin Audio Tech",
                client_email="billing@luminaudio.com",
                total_amount=550.0,
                currency="USD",
                status="PAID",
                due_date=date.today() - timedelta(days=5),
                line_items_json=json.dumps([
                    {"description": "1x Dedicated 60s 4K Instagram Reel", "quantity": 1, "unit_price": 450.0, "total": 450.0},
                    {"description": "2x Instagram Story Frames with Tracked Link", "quantity": 1, "unit_price": 100.0, "total": 100.0}
                ]),
                notes="Thank you for partnering with Alex Rivera Studio! Wire payment received."
            ))

            db.add(Invoice(
                workspace_id=creator_ws.id,
                invoice_number="INV-2026-002",
                client_name="Notion Growth Partner",
                client_email="sponsors@notiongrowth.com",
                total_amount=400.0,
                currency="USD",
                status="SENT",
                due_date=date.today() + timedelta(days=12),
                line_items_json=json.dumps([
                    {"description": "Dedicated Product Placement Reel", "quantity": 1, "unit_price": 400.0, "total": 400.0}
                ]),
                notes="Net 15 payment terms."
            ))
            print("Seeded Alex Rivera (creator@woka.io).")

        # 2. Meta Reviewer Account (meta-reviewer@woka.io)
        reviewer = db.query(User).filter(User.email == "meta-reviewer@woka.io").first()
        if not reviewer:
            reviewer = User(
                email="meta-reviewer@woka.io",
                hashed_password=get_password_hash("MetaReviewer2026!"),
                full_name="Meta Reviewer",
                role="CREATOR",
                avatar_url="https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=150&auto=format&fit=crop&q=80",
                is_active=True,
                is_verified=True
            )
            db.add(reviewer)
            db.flush()

            reviewer_ws = Workspace(name="Meta Reviewer Sandbox", owner_id=reviewer.id)
            db.add(reviewer_ws)
            db.flush()

            db.add(WorkspaceMember(workspace_id=reviewer_ws.id, user_id=reviewer.id, role_in_workspace="OWNER"))

            # Subscription: Pro for Reviewer
            db.add(Subscription(
                workspace_id=reviewer_ws.id,
                plan_tier="PRO",
                status="ACTIVE",
                dm_limit_monthly=2000,
                dm_used_monthly=12,
                ai_limit_monthly=500,
                ai_used_monthly=5
            ))

            # Connected Instagram Account (Sandbox)
            ig_reviewer_account = InstagramAccount(
                workspace_id=reviewer_ws.id,
                ig_user_id="ig_demo_meta_reviewer",
                username="creator_woka_demo",
                name="Woka Demo Creator",
                profile_pic_url="https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=150&auto=format&fit=crop&q=80",
                encrypted_access_token=encrypt_token("sandbox_access_token_reviewer_valid"),
                token_expires_at=datetime.now(timezone.utc) + timedelta(days=60),
                is_connected=True,
                is_sandbox=True,
                followers_count=12400,
                media_count=48
            )
            db.add(ig_reviewer_account)
            db.flush()

            # Reviewer Public Media Kit
            db.add(CreatorProfile(
                workspace_id=reviewer_ws.id,
                slug="metareviewer",
                display_name="Woka Demo Creator",
                bio="Official demonstration profile for Meta App Review testing and automation validation.",
                avatar_url="https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=200&auto=format&fit=crop&q=80",
                niches=json.dumps(["Creator Economy", "Tech", "SaaS"]),
                location="Menlo Park, CA",
                rate_reel=300.0,
                rate_story=100.0,
                rate_bundle=350.0,
                is_verified=True,
                is_public=True
            ))

            # Reviewer Pre-configured Automation
            reviewer_auto = Automation(
                workspace_id=reviewer_ws.id,
                ig_account_id=ig_reviewer_account.id,
                name="Guide Lead Magnet",
                trigger_type="COMMENT",
                target_post_type="ALL_POSTS",
                match_type="CONTAINS_ANY",
                trigger_keywords=json.dumps(["guide", "ebook", "free"]),
                dm_message_template="Hi {{username}}, here is your free guide: https://woka.io/creator-guide",
                reply_comment_template="Just sent the guide to your DMs {{username}}! 🚀",
                is_active=True,
                cooldown_minutes=60,
                total_triggered_count=12
            )
            db.add(reviewer_auto)
            print("Seeded Meta Reviewer (meta-reviewer@woka.io).")

        # 3. Brand User (Elena Vance)
        brand = db.query(User).filter(User.email == "brand@luminaudio.com").first()
        if not brand:
            brand = User(
                email="brand@luminaudio.com",
                hashed_password=get_password_hash("Brand123!"),
                full_name="Elena Vance",
                role="BRAND",
                is_active=True,
                is_verified=True
            )
            db.add(brand)
            db.flush()

            brand_ws = Workspace(name="Lumin Audio Tech", owner_id=brand.id)
            db.add(brand_ws)
            db.flush()
            db.add(WorkspaceMember(workspace_id=brand_ws.id, user_id=brand.id, role_in_workspace="OWNER"))

            camp1 = BrandCampaign(
                brand_workspace_id=brand_ws.id,
                title="Launch Campaign: Studio Wireless Headphone Pro",
                description="We are seeking audio, tech, and productivity creators to review our new noise-cancelling Studio Pro headphones. Showcase real-world desk usage and audio clarity.",
                niche="Tech",
                budget_min=400.0,
                budget_max=900.0,
                required_deliverables=json.dumps(["1x Dedicated Reel (60s)", "2x Story Frames with swipe-up link"]),
                submission_deadline=datetime.now(timezone.utc) + timedelta(days=21),
                status="OPEN"
            )
            db.add(camp1)
            db.flush()

            camp2 = BrandCampaign(
                brand_workspace_id=brand_ws.id,
                title="Productivity Desk Setup & Ergonomics Reel",
                description="Looking for creative workspace lifestyle posts featuring our minimalist aluminum laptop stand.",
                niche="Productivity",
                budget_min=250.0,
                budget_max=600.0,
                required_deliverables=json.dumps(["1x Reel", "1x Story"]),
                submission_deadline=datetime.now(timezone.utc) + timedelta(days=14),
                status="OPEN"
            )
            db.add(camp2)
            db.flush()

            # Proposal from Alex to Lumin Audio (if Alex exists)
            if creator:
                creator_ws = db.query(Workspace).filter(Workspace.owner_id == creator.id).first()
                if creator_ws:
                    app1 = CampaignApplication(
                        campaign_id=camp1.id,
                        creator_workspace_id=creator_ws.id,
                        pitch_text="Hi Elena! My audience is 80% tech enthusiasts and remote workers. I'd love to showcase how the Studio Pro fits into my daily production flow with an aesthetic 4K desk reel.",
                        proposed_rate=550.0,
                        status="ACCEPTED"
                    )
                    db.add(app1)
            print("Seeded Lumin Audio Brand (brand@luminaudio.com).")

        # 4. Admin User (Woka Operations Admin)
        admin = db.query(User).filter(User.email == "admin@woka.io").first()
        if not admin:
            admin = User(
                email="admin@woka.io",
                hashed_password=get_password_hash("Admin123!"),
                full_name="Woka Operations Admin",
                role="ADMIN",
                is_active=True,
                is_verified=True
            )
            db.add(admin)
            db.flush()
            admin_ws = Workspace(name="Woka Headquarters", owner_id=admin.id)
            db.add(admin_ws)
            db.flush()
            db.add(WorkspaceMember(workspace_id=admin_ws.id, user_id=admin.id, role_in_workspace="OWNER"))
            print("Seeded Admin (admin@woka.io).")

        db.commit()
        print("Database seed completed successfully.")

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()

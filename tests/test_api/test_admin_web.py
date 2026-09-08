import pytest
from httpx import ASGITransport, AsyncClient

from app.database.session import get_db
from app.main import app


@pytest.mark.asyncio
async def test_web_admin_dashboard(db_session):
    # Override get_db dependency to use test db_session
    app.dependency_overrides[get_db] = lambda: db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/admin")
        assert res.status_code == 200
        assert "Store Analytics" in res.text
        assert "SELLIFY" in res.text


@pytest.mark.asyncio
async def test_web_admin_products_view(db_session):
    app.dependency_overrides[get_db] = lambda: db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/admin/products")
        assert res.status_code == 200
        assert "Products Catalog" in res.text


@pytest.mark.asyncio
async def test_web_admin_inventory_view(db_session):
    app.dependency_overrides[get_db] = lambda: db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/admin/inventory")
        assert res.status_code == 200
        assert "Bulk Restock Digital Goods" in res.text


@pytest.mark.asyncio
async def test_web_admin_orders_view(db_session):
    app.dependency_overrides[get_db] = lambda: db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/admin/orders")
        assert res.status_code == 200
        assert "Customer Orders" in res.text


@pytest.mark.asyncio
async def test_web_admin_product_lifecycle_and_bulk_stock(db_session):
    from app.database.models.product import ProductCategory
    cat = ProductCategory(name="OTT Streaming", slug="ott-streaming", icon="📺")
    db_session.add(cat)
    await db_session.commit()

    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create new product via Web form
        form_data = {
            "category_id": str(cat.id),
            "name": "Disney Plus Premium",
            "description": "4K Ultra HD account",
            "variant_name": "1 Month Private",
            "price": "2.99",
            "delivery_type": "AUTO_ACCOUNT",
        }
        res_create = await client.post("/admin/products/create", data=form_data, follow_redirects=False)
        assert res_create.status_code == 303

        # 2. Verify product appears in catalog
        res_catalog = await client.get("/admin/products")
        assert "Disney Plus Premium" in res_catalog.text
        assert "1 Month Private" in res_catalog.text

        # Find product ID from DB
        from app.database.repositories.product_repo import ProductRepository
        prod_repo = ProductRepository(db_session)
        products = await prod_repo.get_all_products_with_variants()
        disney = next(p for p in products if p.name == "Disney Plus Premium")
        var_id = disney.variants[0].id

        # 3. Bulk Add Stock via Web form
        bulk_data = {
            "variant_id": str(var_id),
            "payloads_text": "disney_1@test.com:pass1\ndisney_2@test.com:pass2\ndisney_3@test.com:pass3",
        }
        res_stock = await client.post("/admin/inventory/bulk-add", data=bulk_data, follow_redirects=False)
        assert res_stock.status_code == 303

        # Verify stock count is 3
        count = await prod_repo.get_variant_stock_count(var_id)
        assert count == 3

        # 4. Toggle Product active status
        res_toggle = await client.post(f"/admin/products/{disney.id}/toggle", follow_redirects=False)
        assert res_toggle.status_code == 303

        # 5. Delete Product
        res_del = await client.post(f"/admin/products/{disney.id}/delete", follow_redirects=False)
        assert res_del.status_code == 303

        deleted_check = await prod_repo.get_product_by_id(disney.id)
        assert deleted_check is None

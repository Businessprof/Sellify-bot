import os
from decimal import Decimal
from typing import Annotated
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import DeliveryType
from app.database.repositories.inventory_repo import InventoryRepository
from app.database.repositories.order_repo import OrderRepository
from app.database.repositories.product_repo import ProductRepository
from app.database.repositories.user_repo import UserRepository
from app.database.session import get_db

templates_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "web", "templates"))
templates = Jinja2Templates(directory=templates_dir)

router = APIRouter(prefix="/admin", tags=["Admin Web"])


@router.get("", response_class=HTMLResponse)
async def admin_dashboard_view(request: Request, session: AsyncSession = Depends(get_db)):
    user_repo = UserRepository(session)
    order_repo = OrderRepository(session)
    inv_repo = InventoryRepository(session)

    total_users = await user_repo.count_all_users()
    total_stock = await inv_repo.count_all_available_stock()
    metrics = await order_repo.get_overall_metrics()
    recent_orders = await order_repo.get_recent_orders(limit=8)

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "active_page": "dashboard",
            "total_users": total_users,
            "total_stock": total_stock,
            "metrics": metrics,
            "recent_orders": recent_orders,
        },
    )


@router.get("/products", response_class=HTMLResponse)
async def admin_products_view(request: Request, session: AsyncSession = Depends(get_db)):
    prod_repo = ProductRepository(session)
    products = await prod_repo.get_all_products_with_variants()
    categories = await prod_repo.get_active_categories()

    flattened = []
    for p in products:
        for v in p.variants:
            stock = await prod_repo.get_variant_stock_count(v.id)
            flattened.append({
                "id": p.id,
                "variant_id": v.id,
                "name": p.name,
                "category_name": p.category.name if p.category else "Uncategorized",
                "variant_name": v.name,
                "price": v.price,
                "stock": stock,
                "is_active": p.is_active,
                "delivery_type": p.delivery_type.value,
            })

    return templates.TemplateResponse(
        request=request,
        name="products.html",
        context={
            "active_page": "products",
            "products": flattened,
            "categories": categories,
        },
    )


@router.post("/products/create")
async def admin_create_product(
    category_id: Annotated[int, Form()],
    name: Annotated[str, Form()],
    description: Annotated[str, Form()],
    variant_name: Annotated[str, Form()],
    price: Annotated[Decimal, Form()],
    delivery_type: Annotated[str, Form()] = "AUTO_SERIAL",
    session: AsyncSession = Depends(get_db),
):
    prod_repo = ProductRepository(session)
    import secrets
    slug = f"{name.lower().replace(' ', '-')[:30]}-{secrets.token_hex(2)}"
    dtype = DeliveryType(delivery_type)

    await prod_repo.create_product_with_variant(
        category_id=category_id,
        name=name,
        slug=slug,
        description=description,
        delivery_type=dtype,
        variant_name=variant_name,
        price=price,
    )
    await session.commit()
    return RedirectResponse(url="/admin/products", status_code=303)


@router.post("/products/{product_id}/delete")
async def admin_delete_product(product_id: int, session: AsyncSession = Depends(get_db)):
    prod_repo = ProductRepository(session)
    await prod_repo.delete_product(product_id)
    await session.commit()
    return RedirectResponse(url="/admin/products", status_code=303)


@router.post("/products/{product_id}/toggle")
async def admin_toggle_product(product_id: int, session: AsyncSession = Depends(get_db)):
    prod_repo = ProductRepository(session)
    await prod_repo.toggle_product_status(product_id)
    await session.commit()
    return RedirectResponse(url="/admin/products", status_code=303)


@router.get("/inventory", response_class=HTMLResponse)
async def admin_inventory_view(
    request: Request,
    variant_id: int | None = None,
    session: AsyncSession = Depends(get_db),
):
    prod_repo = ProductRepository(session)
    inv_repo = InventoryRepository(session)

    products = await prod_repo.get_all_products_with_variants()
    variants_list = []
    for p in products:
        for v in p.variants:
            st = await prod_repo.get_variant_stock_count(v.id)
            v.stock = st
            v.product = p
            variants_list.append(v)

    total_stock = await inv_repo.count_all_available_stock()

    target_var_id = variant_id if variant_id else (variants_list[0].id if variants_list else None)
    stock_items = []
    if target_var_id:
        stock_items = await inv_repo.get_variant_items(target_var_id, limit=50)

    return templates.TemplateResponse(
        request=request,
        name="inventory.html",
        context={
            "active_page": "inventory",
            "variants": variants_list,
            "selected_variant_id": target_var_id,
            "stock_items": stock_items,
            "total_stock": total_stock,
        },
    )


@router.post("/inventory/bulk-add")
async def admin_bulk_add_stock(
    variant_id: Annotated[int, Form()],
    payloads_text: Annotated[str, Form()],
    session: AsyncSession = Depends(get_db),
):
    prod_repo = ProductRepository(session)
    inv_repo = InventoryRepository(session)

    variant = await prod_repo.get_variant_by_id(variant_id)
    if variant:
        lines = payloads_text.split("\n")
        await inv_repo.bulk_add_stock(product_id=variant.product_id, variant_id=variant.id, payloads=lines)
        await session.commit()

    return RedirectResponse(url=f"/admin/inventory?variant_id={variant_id}", status_code=303)


@router.post("/inventory/{item_id}/delete")
async def admin_delete_stock_item(item_id: str, session: AsyncSession = Depends(get_db)):
    inv_repo = InventoryRepository(session)
    await inv_repo.delete_stock_item(item_id)
    await session.commit()
    return RedirectResponse(url="/admin/inventory", status_code=303)


@router.get("/orders", response_class=HTMLResponse)
async def admin_orders_view(request: Request, session: AsyncSession = Depends(get_db)):
    order_repo = OrderRepository(session)
    orders = await order_repo.get_recent_orders(limit=50)

    return templates.TemplateResponse(
        request=request,
        name="orders.html",
        context={
            "active_page": "orders",
            "orders": orders,
        },
    )

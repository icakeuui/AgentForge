"""
plugin_marketplace.marketplace.service
Marketplace service - manages extension catalog.
"""

from pathlib import Path
import json
from typing import Any, Dict, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from plugin_marketplace.db import Extension
from plugin_marketplace.marketplace.manifest import ManifestParser


class MarketplaceService:
    def __init__(
        self,
        session_or_factory,
        manifests: List[Dict[str, Any]] | None = None,
    ):
        """
        Args:
            session_or_factory: Either an AsyncSession or async_sessionmaker
            manifests: List of loaded manifest dicts (for seeding)
        """
        if isinstance(session_or_factory, async_sessionmaker):
            self._session_factory = session_or_factory
        else:
            self._session_factory = None
        self._session = session_or_factory if not isinstance(session_or_factory, async_sessionmaker) else None
        self.manifests = manifests or []

    async def _get_session(self) -> AsyncSession:
        if self._session_factory:
            return self._session_factory()
        return self._session

    async def seed_extensions(self) -> None:
        """Seed all manifests into the database."""
        parser = ManifestParser()
        for manifest in self.manifests:
            await self._upsert_extension(manifest, parser)

    async def _upsert_extension(self, manifest: Dict[str, Any], parser: ManifestParser) -> None:
        parsed = parser.parse_manifest(manifest)
        runtime = parsed.get("runtime", {})
        install = parsed.get("install", {})

        if self._session_factory:
            from contextlib import asynccontextmanager

            @asynccontextmanager
            async def _ctx():
                async with self._session_factory() as sess:
                    yield sess

            ctx = _ctx()
            session = await ctx.__aenter__()
            try:
                await self._do_upsert(session, parsed, runtime, install)
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await ctx.__aexit__(None, None, None)
        else:
            await self._do_upsert(self._session, parsed, runtime, install)
            await self._session.commit()

    async def _do_upsert(
        self,
        session: AsyncSession,
        parsed: Dict[str, Any],
        runtime: Dict[str, Any],
        install: Dict[str, Any],
    ) -> None:
        ext_id = parsed["id"]
        result = await session.execute(select(Extension).where(Extension.id == ext_id))
        extension = result.scalar_one_or_none()

        if not extension:
            extension = Extension(id=ext_id, name=parsed["name"], tool_type=parsed["tool_type"])
            session.add(extension)

        extension.name = parsed.get("name", extension.name)
        extension.description = parsed.get("description")
        extension.icon_url = parsed.get("icon_url")
        extension.tool_type = parsed.get("tool_type", extension.tool_type)
        extension.manifest = parsed.get("manifest", {})
        extension.install_command = install.get("command")
        extension.uninstall_command = install.get("uninstall_command")
        extension.mcp_transport = runtime.get("transport")
        extension.mcp_command = install.get("command")
        mcp_args_val = install.get("args", []); extension.mcp_args = json.dumps(mcp_args_val) if mcp_args_val else None
        mcp_env = {k: "" for k in runtime.get("env_vars", [])}; extension.mcp_env_vars = json.dumps(mcp_env) if mcp_env else None
        extension.mcp_url = runtime.get("url")
        categories_val = parsed.get("categories", []); extension.categories = json.dumps(categories_val) if categories_val else None
        extension.author = parsed.get("author")
        extension.homepage = parsed.get("homepage")
        extension.popularity = parsed.get("popularity", 0)
        extension.is_official = parsed.get("is_official", False)
        extension.status = "available"

    async def list_extensions(self) -> List[Dict[str, Any]]:
        """List all available extensions."""
        if self._session_factory:
            async with self._session_factory() as session:
                result = await session.execute(select(Extension).order_by(Extension.popularity.desc()))
                rows = result.scalars().all()
                return [self._ext_to_dict(e) for e in rows]
        else:
            result = await self._session.execute(select(Extension).order_by(Extension.popularity.desc()))
            rows = result.scalars().all()
            return [self._ext_to_dict(e) for e in rows]

    async def list_extension_records(self) -> List[Extension]:
        """Return ORM extension rows for internal adapter/bootstrap use."""
        if self._session_factory:
            async with self._session_factory() as session:
                result = await session.execute(select(Extension).order_by(Extension.popularity.desc()))
                return list(result.scalars().all())
        result = await self._session.execute(select(Extension).order_by(Extension.popularity.desc()))
        return list(result.scalars().all())

    def _ext_to_dict(self, ext: Extension) -> Dict[str, Any]:
        manifest = ext.manifest or {}
        return {
            "id": ext.id,
            "name": ext.name,
            "description": ext.description,
            "icon_url": ext.icon_url,
            "tool_type": ext.tool_type,
            "categories": json.loads(ext.categories) if ext.categories else [],
            "author": ext.author,
            "homepage": ext.homepage,
            "popularity": ext.popularity,
            "is_official": ext.is_official,
            "status": ext.status,
            "config_fields": manifest.get("config", []),
        }

'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import Image from 'next/image'
import { useTranslations } from 'next-intl'
import { Building2, ChevronDown, LogOut, Search } from 'lucide-react'

import { useAuth } from '@/lib/contexts/AuthContext'
import { getApiUrl } from '@/lib/api/client'
import { GlobalSearch } from '@/components/search'
import { ScrollArea } from '@/components/ui/scroll-area'
import { useModules } from '@/lib/api/queries'
import { useNavigationState } from '@/hooks/useNavigationState'
import { navigationGroups, type NavGroup } from '@/lib/config/navigation'
import { cn } from '@/lib/utils'

interface SidebarProps {
  isOpen?: boolean
  onClose?: () => void
}

export function Sidebar({ isOpen = false }: SidebarProps) {
  const pathname = usePathname()
  const router = useRouter()
  const t = useTranslations('nav')
  const { user, tenant, logout } = useAuth()
  const { data: modulesData } = useModules()
  const { isExpanded, toggleGroup, hydrated } = useNavigationState()
  const [isSearchOpen, setIsSearchOpen] = useState(false)

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setIsSearchOpen(true)
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [])

  const handleLogout = async () => {
    try {
      await logout()
      router.push('/login')
    } catch (err) {
      console.error('Logout error:', err)
    }
  }

  const isActive = (path: string) =>
    pathname === path || pathname.startsWith(path + '/')

  const isGroupVisible = (group: NavGroup): boolean => {
    if (group.adminOnly && !(user?.is_tenant_owner || user?.role === 'admin')) {
      return false
    }
    if (group.module && modulesData) {
      return modulesData.modules.includes(group.module)
    }
    return true
  }

  const initials = `${user?.first_name?.charAt(0) ?? ''}${user?.last_name?.charAt(0) ?? ''}`
  // Tenant logo uses string-typed optional property (not yet on the Tenant
  // interface — backend exposes it dynamically). Cast to avoid the TS hole.
  const tenantLogo = (tenant as { logo?: string } | null)?.logo

  return (
    <aside
      className={cn(
        'flex flex-col h-screen fixed left-0 top-0 z-50 transition-transform duration-200 ease-in-out lg:translate-x-0',
        isOpen ? 'translate-x-0' : '-translate-x-full'
      )}
      style={{
        width: 240,
        backgroundColor: 'var(--color-tenant-primary)',
      }}
    >
      {/* Logo & Tenant */}
      <div className="px-5 py-5 border-b border-white/10">
        {tenantLogo ? (
          <img
            src={
              tenantLogo.startsWith('http')
                ? tenantLogo
                : `${getApiUrl()}${tenantLogo}`
            }
            alt={tenant?.business_name ?? 'Logo'}
            className="h-7 w-auto object-contain mb-3 brightness-0 invert"
          />
        ) : (
          <Image
            src="/logo.svg"
            alt="CrediFlux"
            width={130}
            height={32}
            className="h-7 w-auto mb-3 brightness-0 invert"
            priority
          />
        )}
        {tenant && (
          <div className="flex items-center gap-1.5 text-xs text-white/40 mt-2">
            <Building2 className="h-3 w-3 shrink-0" />
            <span className="truncate">{tenant.business_name}</span>
          </div>
        )}

        <button
          onClick={() => setIsSearchOpen(true)}
          className="mt-4 w-full flex items-center justify-between px-3 py-2 rounded-md text-xs text-white/50 bg-white/5 hover:bg-white/10 transition-colors"
        >
          <div className="flex items-center gap-2">
            <Search className="h-3.5 w-3.5" />
            <span>{t('search')}</span>
          </div>
          <kbd
            className="px-1.5 py-0.5 bg-white/10 rounded text-white/40"
            style={{ fontSize: 10 }}
          >
            ⌘K
          </kbd>
        </button>
      </div>

      <GlobalSearch isOpen={isSearchOpen} onClose={() => setIsSearchOpen(false)} />

      {/* Navigation groups */}
      <ScrollArea className="flex-1">
        <nav className="px-3 py-4">
          {navigationGroups.filter(isGroupVisible).map((group) => {
            // Overview and admin render flat (no collapse affordance),
            // everything else is a collapsible group.
            const isFlatGroup = group.id === 'overview' || group.id === 'admin'
            const expanded = isFlatGroup || !hydrated || isExpanded(group.id)
            const anySubActive = group.items.some((item) => isActive(item.href))

            return (
              <div key={group.id} className="mb-4">
                {!isFlatGroup ? (
                  <button
                    onClick={() => toggleGroup(group.id)}
                    className={cn(
                      'w-full flex items-center justify-between px-3 py-1.5 mb-0.5 rounded-md text-[10px] font-semibold uppercase tracking-widest transition-colors',
                      anySubActive
                        ? 'text-white/80'
                        : 'text-white/30 hover:text-white/60'
                    )}
                  >
                    <span>{t(group.labelKey)}</span>
                    <ChevronDown
                      className={cn(
                        'h-3 w-3 transition-transform',
                        expanded ? 'rotate-0' : '-rotate-90'
                      )}
                    />
                  </button>
                ) : (
                  <p className="px-3 mb-1.5 text-[10px] font-semibold uppercase tracking-widest text-white/30">
                    {t(group.labelKey)}
                  </p>
                )}

                {expanded && (
                  <div className="space-y-0.5">
                    {group.items.map((item) => {
                      const Icon = item.icon
                      const active = isActive(item.href)
                      return (
                        <Link
                          key={item.href}
                          href={item.href}
                          className={cn(
                            'relative flex items-center gap-2.5 px-3 py-2 rounded-md text-sm transition-colors',
                            active
                              ? 'text-white bg-white/10'
                              : 'text-white/60 hover:text-white hover:bg-white/5'
                          )}
                        >
                          {active && (
                            <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 rounded-r-full bg-sun" />
                          )}
                          <Icon className="h-4 w-4 shrink-0" />
                          <span>{t(item.labelKey)}</span>
                        </Link>
                      )
                    })}
                  </div>
                )}
              </div>
            )
          })}
        </nav>
      </ScrollArea>

      {/* User Profile */}
      <div className="px-3 py-4 border-t border-white/10">
        <div className="flex items-center gap-3 px-2 mb-2">
          <div className="h-8 w-8 rounded-full bg-sage flex items-center justify-center text-white text-xs font-semibold shrink-0">
            {initials}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-white truncate leading-tight">
              {user?.full_name}
            </p>
            <p className="text-xs text-white/40 capitalize truncate">
              {user?.role?.replace('_', ' ')}
            </p>
          </div>
        </div>
        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-2.5 px-3 py-2 rounded-md text-sm text-white/50 hover:text-white hover:bg-white/5 transition-colors"
        >
          <LogOut className="h-4 w-4 shrink-0" />
          <span>{t('logout')}</span>
        </button>
      </div>
    </aside>
  )
}

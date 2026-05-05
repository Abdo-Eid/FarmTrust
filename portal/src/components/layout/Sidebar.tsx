"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { clsx } from "clsx";
import { useState } from "react";
import { authClient } from "@/lib/auth-client";

const NAV_ITEMS = [
    { href: "/lands", icon: "grid_view", label: "Lands" },
    { href: "/admin", icon: "manage_accounts", label: "Admin" },
];

export function Sidebar() {
    const pathname = usePathname();
    const { data: session } = authClient.useSession();
    const [isCollapsed, setIsCollapsed] = useState(true);

    return (
        <aside
            className={clsx(
                "flex-shrink-0 bg-teal-900 flex flex-col h-full transition-all duration-200",
                isCollapsed ? "w-20" : "w-60",
            )}
        >
            {/* Logo */}
            <div
                className={clsx(
                    "border-b border-teal-800",
                    isCollapsed ? "px-3 py-5" : "px-5 py-5",
                )}
            >
                <div
                    className={clsx(
                        "flex items-center",
                        isCollapsed ? "justify-center" : "gap-2.5",
                    )}
                >
                    <div className="w-7 h-7 rounded-md bg-teal-gradient flex items-center justify-center flex-shrink-0">
                        <span className="material-symbols-outlined text-white text-base">
                            satellite_alt
                        </span>
                    </div>
                    {!isCollapsed && (
                        <div>
                            <p className="text-white text-sm font-semibold leading-none">
                                FarmTrust
                            </p>
                            <p className="text-teal-500 text-xs mt-0.5">
                                Land Intelligence
                            </p>
                        </div>
                    )}
                </div>
                <div
                    className={clsx(
                        "mt-4 flex",
                        isCollapsed ? "justify-center" : "justify-end",
                    )}
                >
                    <button
                        type="button"
                        onClick={() => setIsCollapsed((current) => !current)}
                        className="inline-flex h-8 w-8 items-center justify-center rounded-md text-teal-200 transition-colors hover:bg-teal-800 hover:text-white"
                        aria-label={
                            isCollapsed ? "Expand sidebar" : "Collapse sidebar"
                        }
                        title={
                            isCollapsed ? "Expand sidebar" : "Collapse sidebar"
                        }
                    >
                        <span className="material-symbols-outlined text-base">
                            {isCollapsed ? "chevron_right" : "chevron_left"}
                        </span>
                    </button>
                </div>
            </div>

            {/* Nav */}
            <nav
                className={clsx(
                    "flex-1 py-4 space-y-0.5",
                    isCollapsed ? "px-2" : "px-3",
                )}
            >
                {!isCollapsed && (
                    <p className="text-teal-600 text-xs font-semibold uppercase tracking-widest px-2 mb-3">
                        Navigation
                    </p>
                )}
                {NAV_ITEMS.map((item) => {
                    const active = pathname.startsWith(item.href);
                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            title={isCollapsed ? item.label : undefined}
                            className={clsx(
                                "rounded-md text-sm transition-colors",
                                isCollapsed
                                    ? "flex justify-center px-2 py-3"
                                    : "flex items-center gap-3 px-3 py-2",
                                active
                                    ? isCollapsed
                                        ? "bg-teal-800 text-white"
                                        : "bg-teal-800 text-white border-l-2 border-teal-600 pl-[10px]"
                                    : "text-teal-100 hover:bg-teal-800/60 hover:text-white",
                            )}
                        >
                            <span className="material-symbols-outlined text-[18px]">
                                {item.icon}
                            </span>
                            {!isCollapsed && item.label}
                        </Link>
                    );
                })}
            </nav>

            {/* User section */}
            <div
                className={clsx(
                    "border-t border-teal-800 py-4",
                    isCollapsed ? "px-3" : "px-4",
                )}
            >
                <div
                    className={clsx(
                        "flex items-center",
                        isCollapsed ? "justify-center" : "gap-3",
                    )}
                >
                    <div className="w-8 h-8 rounded-full bg-teal-700 flex items-center justify-center flex-shrink-0">
                        <span className="material-symbols-outlined text-teal-200 text-base">
                            person
                        </span>
                    </div>
                    {!isCollapsed && (
                        <div className="min-w-0 flex-1">
                            <p className="text-white text-xs font-medium truncate">
                                {session?.user?.name ?? "—"}
                            </p>
                            <p className="text-teal-400 text-xs truncate">
                                {(session?.user as { institution?: string })
                                    ?.institution ??
                                    session?.user?.email ??
                                    ""}
                            </p>
                        </div>
                    )}
                    <button
                        onClick={() =>
                            authClient.signOut({
                                fetchOptions: {
                                    onSuccess: () => {
                                        window.location.href = "/login";
                                    },
                                },
                            })
                        }
                        className={clsx(
                            "transition-colors",
                            isCollapsed
                                ? "text-teal-300 hover:text-teal-100"
                                : "text-teal-500 hover:text-teal-200",
                        )}
                        title="Sign out"
                    >
                        <span className="material-symbols-outlined text-base">
                            logout
                        </span>
                    </button>
                </div>
            </div>
        </aside>
    );
}

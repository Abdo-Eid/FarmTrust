"use client";

import Link from "next/link";

export function HeroPage() {
    return (
        <div className="flex min-h-screen flex-col bg-sand">
            {/* Top navigation */}
            <header className="flex items-center justify-between px-8 py-4">
                <div className="flex items-center gap-3">
                    <div className="flex h-9 w-9 items-center justify-center rounded-md bg-teal-gradient flex-shrink-0">
                        <span className="material-symbols-outlined text-white text-xl">
                            satellite_alt
                        </span>
                    </div>
                    <div>
                        <p className="text-gray-900 text-lg font-semibold leading-none">
                            FarmTrust
                        </p>
                        <p className="text-gray-500 text-xs mt-0.5">
                            Land Intelligence
                        </p>
                    </div>
                </div>
                <div className="flex items-center gap-4">
                    <Link
                        href="/login"
                        className="text-sm text-gray-600 font-medium transition-colors hover:text-gray-900"
                    >
                        Sign In
                    </Link>
                    <Link
                        href="/login"
                        className="inline-flex items-center rounded-md bg-teal-700 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-teal-800"
                    >
                        Get Started
                        <span className="material-symbols-outlined ml-1.5 text-base">
                            arrow_forward
                        </span>
                    </Link>
                </div>
            </header>

            {/* Hero section */}
            <section className="relative flex flex-1 flex-col items-center justify-center px-6 pt-16 pb-24">
                {/* Decorative tech-grid background */}
                <div
                    className="pointer-events-none absolute inset-0 opacity-[0.03]"
                    style={{
                        backgroundImage: `url("data:image/svg+xml,%3Csvg width='40' height='40' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M 40 0 L 0 0 0 40' fill='none' stroke='%23000' stroke-width='1'/%3E%3C/svg%3E")`,
                    }}
                />

                <div className="relative mx-auto max-w-4xl text-center">
                    {/* Badge */}
                    <div className="mb-6 inline-flex items-center gap-1.5 rounded-full border border-teal-200 bg-teal-50 px-3 py-1">
                        <span className="h-1.5 w-1.5 rounded-full bg-teal-600" />
                        <span className="text-xs font-medium text-teal-700">
                            Satellite-Powered Land Intelligence
                        </span>
                    </div>

                    {/* Heading */}
                    <h1 className="text-4xl font-bold tracking-tight text-gray-900 sm:text-5xl lg:text-6xl">
                        Know the land.{" "}
                        <span className="bg-teal-gradient bg-clip-text text-transparent">
                            Before you lend.
                        </span>
                    </h1>

                    {/* Subtitle */}
                    <p className="mx-auto mt-6 max-w-2xl text-base leading-relaxed text-gray-500 sm:text-lg">
                        FarmTrust transforms multi-year satellite time-series
                        into objective, continuous land activity signals — so
                        agricultural financing decisions are grounded in data,
                        not field visits.
                    </p>

                    {/* CTA buttons */}
                    <div className="mt-10 flex items-center justify-center gap-4">
                        <Link
                            href="/login"
                            className="inline-flex items-center rounded-md bg-teal-700 px-6 py-3 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-teal-800"
                        >
                            Enter Portal
                            <span className="material-symbols-outlined ml-2 text-base">
                                arrow_forward
                            </span>
                        </Link>
                        <a
                            href="#how-it-works"
                            className="inline-flex items-center rounded-md border border-gray-300 bg-white px-6 py-3 text-sm font-semibold text-gray-700 shadow-sm transition-colors hover:bg-gray-50"
                        >
                            <span className="material-symbols-outlined mr-2 text-base">
                                play_arrow
                            </span>
                            How It Works
                        </a>
                    </div>
                </div>

                {/* Feature cards */}
                <div className="relative mx-auto mt-24 grid w-full max-w-5xl gap-6 sm:grid-cols-2 lg:grid-cols-4">
                    {[
                        {
                            icon: "satellite_alt",
                            title: "Multi-Year Time-Series",
                            desc: "24-month NDVI, NDWI, and vegetation indices from Sentinel-2 & Landsat 8.",
                        },
                        {
                            icon: "analytics",
                            title: "Activity Scoring",
                            desc: "Objective cultivation, fallow, evidence coverage, and assessment confidence per land parcel.",
                        },
                        {
                            icon: "description",
                            title: "Shareable Reports",
                            desc: "One-click PDF reports built for lender workflows and compliance.",
                        },
                        {
                            icon: "public",
                            title: "Egypt Coverage",
                            desc: "Starting with the Nile Delta and expanding to new regions incrementally.",
                        },
                    ].map((card) => (
                        <div
                            key={card.title}
                            className="group rounded-md border border-gray-200 bg-white p-6 shadow-panel transition-shadow hover:shadow-panel-md"
                        >
                            <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-md bg-teal-50 transition-colors group-hover:bg-teal-100">
                                <span className="material-symbols-outlined text-teal-700 text-xl">
                                    {card.icon}
                                </span>
                            </div>
                            <h3 className="text-sm font-semibold text-gray-900">
                                {card.title}
                            </h3>
                            <p className="mt-1.5 text-xs leading-relaxed text-gray-500">
                                {card.desc}
                            </p>
                        </div>
                    ))}
                </div>
            </section>

            {/* How it works section */}
            <section id="how-it-works" className="bg-teal-900 px-6 py-20">
                <div className="mx-auto max-w-5xl">
                    <div className="mb-14 text-center">
                        <h2 className="text-2xl font-bold text-white sm:text-3xl">
                            From satellite pixels to financing signals
                        </h2>
                        <p className="mt-3 text-sm text-teal-300">
                            A transparent, auditable pipeline — no black boxes.
                        </p>
                    </div>

                    <div className="grid gap-8 sm:grid-cols-3">
                        {[
                            {
                                step: "01",
                                title: "Ingest & Align",
                                desc: "Multi-source satellite data is ingested, cloud-masked, and aligned to parcel boundaries.",
                            },
                            {
                                step: "02",
                                title: "Analyze & Score",
                                desc: "Vegetation indices are computed, smoothed, and classified into activity evidence signals.",
                            },
                            {
                                step: "03",
                                title: "Report & Decide",
                                desc: "Consolidated scores, trends, evidence coverage, and assessment-confidence bands are delivered via portal or PDF.",
                            },
                        ].map((item) => (
                            <div key={item.step} className="text-center">
                                <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-teal-800">
                                    <span className="text-lg font-bold text-teal-500">
                                        {item.step}
                                    </span>
                                </div>
                                <h3 className="text-base font-semibold text-white">
                                    {item.title}
                                </h3>
                                <p className="mt-2 text-xs leading-relaxed text-teal-300">
                                    {item.desc}
                                </p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Footer */}
            <footer className="border-t border-gray-200 bg-white px-6 py-8">
                <div className="mx-auto flex max-w-5xl items-center justify-between">
                    <div className="flex items-center gap-2">
                        <span className="material-symbols-outlined text-teal-700 text-base">
                            satellite_alt
                        </span>
                        <span className="text-xs text-gray-500">
                            FarmTrust · NeuralAlloy
                        </span>
                    </div>
                    <p className="text-xs text-gray-400">v0.1 MVP</p>
                </div>
            </footer>
        </div>
    );
}

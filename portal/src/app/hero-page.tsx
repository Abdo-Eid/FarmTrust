import Link from "next/link";
import {
    ArrowRight,
    BarChart3,
    FileText,
    Globe2,
    Play,
    Satellite,
} from "lucide-react";

const FEATURE_CARDS = [
    {
        icon: Satellite,
        title: "Multi-Year Time-Series",
        desc: "24-month Sentinel-2 vegetation and moisture evidence for each land parcel.",
    },
    {
        icon: BarChart3,
        title: "Risk Evidence",
        desc: "Land status, trend, latest-season performance, evidence coverage, and assessment confidence.",
    },
    {
        icon: FileText,
        title: "Shareable Reports",
        desc: "One-click PDF reports built for lender workflows and review.",
    },
    {
        icon: Globe2,
        title: "Egypt Coverage",
        desc: "Current-build assessment coverage is focused on Egypt, with conservative satellite-only signals.",
    },
] as const;

export function HeroPage() {
    return (
        <div className="flex min-h-screen flex-col bg-sand">
            {/* Top navigation */}
            <header className="flex items-center justify-between px-8 py-4">
                <div className="flex items-center gap-3">
                    <div className="flex h-9 w-9 items-center justify-center rounded-md bg-teal-gradient flex-shrink-0">
                        <Satellite className="h-5 w-5 text-white" aria-hidden="true" />
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
                        href="/lands"
                        className="inline-flex items-center rounded-md bg-teal-700 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-teal-800"
                    >
                        Open Interface
                        <ArrowRight className="ml-1.5 h-4 w-4" aria-hidden="true" />
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
                            Satellite-Powered Land Intelligence Interface
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
                        FarmTrust turns satellite time-series evidence into
                        lender-facing farm risk reports, helping financiers
                        review agricultural credit-readiness with clear
                        confidence notes and decision-support signals.
                    </p>

                    {/* CTA buttons */}
                    <div className="mt-10 flex items-center justify-center gap-4">
                        <Link
                            href="/lands"
                            className="inline-flex items-center rounded-md bg-teal-700 px-6 py-3 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-teal-800"
                        >
                            Open Lands
                            <ArrowRight className="ml-2 h-4 w-4" aria-hidden="true" />
                        </Link>
                        <a
                            href="#how-it-works"
                            className="inline-flex items-center rounded-md border border-gray-300 bg-white px-6 py-3 text-sm font-semibold text-gray-700 shadow-sm transition-colors hover:bg-gray-50"
                        >
                            <Play className="mr-2 h-4 w-4" aria-hidden="true" />
                            How It Works
                        </a>
                    </div>
                </div>

                {/* Feature cards */}
                <div className="relative mx-auto mt-24 grid w-full max-w-5xl gap-6 sm:grid-cols-2 lg:grid-cols-4">
                    {FEATURE_CARDS.map((card) => {
                        const Icon = card.icon;
                        return (
                            <div
                                key={card.title}
                                className="group rounded-md border border-gray-200 bg-white p-6 shadow-panel transition-shadow hover:shadow-panel-md"
                            >
                                <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-md bg-teal-50 transition-colors group-hover:bg-teal-100">
                                    <Icon className="h-5 w-5 text-teal-700" aria-hidden="true" />
                                </div>
                                <h3 className="text-sm font-semibold text-gray-900">
                                    {card.title}
                                </h3>
                                <p className="mt-1.5 text-xs leading-relaxed text-gray-500">
                                    {card.desc}
                                </p>
                            </div>
                        );
                    })}
                </div>
            </section>

            {/* How it works section */}
            <section id="how-it-works" className="bg-teal-900 px-6 py-20">
                <div className="mx-auto max-w-5xl">
                    <div className="mb-14 text-center">
                        <h2 className="text-2xl font-bold text-white sm:text-3xl">
                            From satellite pixels to work-ready signals
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
                                desc: "Sentinel-2 observations are ingested, cloud-masked, and aligned to land boundaries.",
                            },
                            {
                                step: "02",
                                title: "Analyze Evidence",
                                desc: "Vegetation and moisture signals are smoothed into status, trend, season, and risk evidence.",
                            },
                            {
                                step: "03",
                                title: "Report & Review",
                                desc: "Risk tier, flags, evidence coverage, and confidence notes are delivered through the portal and PDF report.",
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
                        <Satellite className="h-4 w-4 text-teal-700" aria-hidden="true" />
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

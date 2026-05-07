"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { authClient } from "@/lib/auth-client";
import { Button } from "@/components/ui/Button";
import { FormField, Input } from "@/components/ui/FormField";

const schema = z.object({
    email: z.string().email("Enter a valid email"),
    password: z.string().min(1, "Password is required"),
});

type FormData = z.infer<typeof schema>;

export default function LoginPage() {
    const router = useRouter();
    const [authError, setAuthError] = useState<string | null>(null);
    const { data: session, isPending } = authClient.useSession();

    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);

    useEffect(() => {
        if (!isPending && session) {
            router.replace("/lands");
        }
    }, [session, isPending, router]);

    if (isPending) {
        return (
            <div className="flex h-screen items-center justify-center bg-sand">
                <div className="h-8 w-8 animate-spin rounded-full border-2 border-teal-600 border-t-transparent" />
            </div>
        );
    }

    if (session) {
        return null;
    }

    const onSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsSubmitting(true);
        setAuthError(null);
        const { error } = await authClient.signIn.email({
            email,
            password,
            callbackURL: "/lands",
        });
        if (error) {
            setAuthError(
                "Invalid credentials. Try analyst@farmtrust.eg / demo123",
            );
            setIsSubmitting(false);
        } else {
            router.push("/lands");
        }
    };

    return (
        <div className="flex h-screen">
            {/* Left panel — identity */}
            <div className="relative w-2/5 flex-shrink-0 bg-teal-900 flex flex-col overflow-hidden">
                {/* Teal gradient header band */}
                <div className="h-1.5 bg-teal-gradient flex-shrink-0" />

                {/* Tech-grid overlay */}
                <div
                    className="absolute inset-0 bg-tech-grid pointer-events-none"
                    aria-hidden
                    style={{ top: "6px" }}
                />

                <div className="relative flex flex-col flex-1 px-10 py-12">
                    {/* Logo — links to hero */}
                    <a href="/" className="flex items-center gap-3 mb-auto">
                        <div className="w-9 h-9 rounded-md bg-teal-gradient flex items-center justify-center flex-shrink-0">
                            <span className="material-symbols-outlined text-white text-xl">
                                satellite_alt
                            </span>
                        </div>
                        <div>
                            <p className="text-white text-lg font-semibold leading-none">
                                FarmTrust
                            </p>
                            <p className="text-teal-500 text-xs mt-0.5">
                                Land Intelligence Portal
                            </p>
                        </div>
                    </a>

                    {/* Tagline */}
                    <div className="py-12">
                        <h1 className="text-white text-2xl font-bold leading-snug mb-4">
                            Satellite-based land assessment for agricultural
                            financing decisions.
                        </h1>
                        <p className="text-teal-300 text-sm leading-relaxed">
                            Continuous, objective land activity signals derived
                            from multi-year satellite time-series — no field
                            visits required.
                        </p>
                    </div>

                    {/* Feature bullets */}
                    <div className="space-y-3 mb-auto">
                        {[
                            {
                                icon: "eco",
                                text: "24-month vegetation analysis",
                            },
                            {
                                icon: "analytics",
                                text: "Risk scoring & confidence bands",
                            },
                            {
                                icon: "description",
                                text: "Shareable PDF reports for lenders",
                            },
                            {
                                icon: "location_on",
                                text: "Egypt-wide coverage (MVP)",
                            },
                        ].map((item) => (
                            <div
                                key={item.icon}
                                className="flex items-center gap-3"
                            >
                                <span className="material-symbols-outlined text-teal-500 text-base">
                                    {item.icon}
                                </span>
                                <span className="text-teal-200 text-sm">
                                    {item.text}
                                </span>
                            </div>
                        ))}
                    </div>

                    <p className="text-teal-700 text-xs mt-8">
                        NeuralAlloy · FarmTrust v0.1 MVP
                    </p>
                </div>
            </div>

            {/* Right panel — form */}
            <div className="flex-1 bg-sand flex items-center justify-center px-12">
                <div className="w-full max-w-sm">
                    <div className="mb-8">
                        <h2 className="text-gray-900 text-xl font-semibold">
                            Sign in to your account
                        </h2>
                        <p className="text-gray-500 text-sm mt-1">
                            Institutional access only
                        </p>
                    </div>

                    <form onSubmit={onSubmit} className="space-y-4">
                        <FormField label="Email Address" required>
                            <Input
                                type="email"
                                placeholder="analyst@farmtrust.eg"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                            />
                        </FormField>

                        <FormField label="Password" required>
                            <Input
                                type="password"
                                placeholder="••••••••"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                            />
                        </FormField>

                        {authError && (
                            <div className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-md">
                                <span className="material-symbols-outlined text-red-500 text-sm mt-0.5">
                                    error
                                </span>
                                <p className="text-xs text-red-700">
                                    {authError}
                                </p>
                            </div>
                        )}

                        <Button
                            type="submit"
                            variant="primary"
                            size="lg"
                            loading={isSubmitting}
                            className="w-full mt-2"
                        >
                            Sign In
                        </Button>
                    </form>

                    {/* TODO: remove this block before production — exposes mock credentials */}
                    <div className="mt-6 p-3 bg-teal-50 border border-teal-200 rounded-md">
                        <p className="text-xs font-semibold text-teal-700 mb-1.5">
                            Demo Credentials
                        </p>
                        <p className="text-xs text-teal-600 font-mono">
                            analyst@farmtrust.eg
                        </p>
                        <p className="text-xs text-teal-600 font-mono">
                            demo123
                        </p>
                    </div>

                    <p className="text-xs text-gray-400 text-center mt-6">
                        Access is restricted to authorized institutions.
                    </p>
                </div>
            </div>
        </div>
    );
}

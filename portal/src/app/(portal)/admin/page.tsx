import { PageHeader } from "@/components/layout/PageHeader";
import { Card, CardHeader, CardTitle } from "@/components/ui/Card";

export default function AdminPage() {
    return (
        <div className="min-h-screen bg-gray-50">
            <PageHeader
                title="System Operations"
                subtitle="Portal and pipeline interface status"
            />

            <div className="grid gap-6 p-6 lg:grid-cols-3">
                <Card className="lg:col-span-2">
                    <CardHeader>
                        <CardTitle>Portal Role</CardTitle>
                    </CardHeader>
                    <div className="space-y-3 text-sm text-gray-600">
                        <p>
                            This interface is the entry point to the work
                            already produced by the FarmTrust pipeline.
                        </p>
                        <p>
                            It surfaces lands, assessments, evidence, and report
                            exports without any sign-in step.
                        </p>
                    </div>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle>Backend Connection</CardTitle>
                    </CardHeader>
                    <div className="space-y-2 text-sm text-gray-600">
                        <p>
                            API base URL:{" "}
                            {process.env.NEXT_PUBLIC_API_BASE || "/api"}
                        </p>
                        <p>Environment: Development</p>
                    </div>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle>Quick Actions</CardTitle>
                    </CardHeader>
                    <div className="space-y-3 text-sm text-gray-600">
                        <p>
                            Open the lands list to review active cases and
                            reports.
                        </p>
                        <a
                            href="/lands"
                            className="inline-flex items-center rounded-md bg-teal-700 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-teal-800"
                        >
                            Go to Lands
                        </a>
                    </div>
                </Card>
            </div>
        </div>
    );
}

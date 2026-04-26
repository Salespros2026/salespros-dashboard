import { signIn } from "@/auth";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export const dynamic = "force-dynamic";

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ callbackUrl?: string; error?: string }>;
}) {
  const params = await searchParams;

  return (
    <div className="flex-1 flex items-center justify-center px-6">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle className="text-xl">Salespros Dashboard</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Logowanie ograniczone do whitelisty email. Zaloguj się przez Google.
          </p>
          {params.error && (
            <div className="text-sm text-rose-400 border border-rose-500/30 bg-rose-500/10 rounded p-3">
              Brak dostępu. Twój email nie jest na whiteliście. Skontaktuj się z administratorem.
            </div>
          )}
          <form
            action={async () => {
              "use server";
              await signIn("google", { redirectTo: params.callbackUrl || "/" });
            }}
          >
            <Button type="submit" className="w-full">
              Zaloguj przez Google
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

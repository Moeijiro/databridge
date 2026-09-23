"use client";

import { useParams } from "next/navigation";
import { IntegrationForm } from "@/components/app/integration-form";
import { ErrorState, PageLoading, PageTitle } from "@/components/app/ui";
import { useApi } from "@/hooks/use-api";
import { api } from "@/lib/api";

export default function EditIntegrationPage() {
  const { id } = useParams<{ id: string }>();
  const integration = useApi(() => api.integration(Number(id)), `integration-${id}`);
  if (integration.loading) return <PageLoading />;
  if (integration.error || !integration.data) return <ErrorState message={integration.error ?? "Not found."} />;
  return (
    <>
      <PageTitle title={`Edit ${integration.data.name}`} />
      <IntegrationForm initial={integration.data} />
    </>
  );
}

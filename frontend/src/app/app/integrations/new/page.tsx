import { IntegrationForm } from "@/components/app/integration-form";
import { PageTitle } from "@/components/app/ui";

export default function NewIntegrationPage() {
  return (
    <>
      <PageTitle title="New integration" description="Source → field mapping → destination. Test each side before saving." />
      <IntegrationForm />
    </>
  );
}

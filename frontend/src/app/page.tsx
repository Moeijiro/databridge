import { Footer, Hero, How, Mapping, Nav, Reliability, UseCases } from "@/components/site/landing";

export default function Home() {
  return (
    <>
      <Nav />
      <main id="main">
        <Hero />
        <How />
        <Mapping />
        <Reliability />
        <UseCases />
      </main>
      <Footer />
    </>
  );
}

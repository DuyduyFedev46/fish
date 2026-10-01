import React, { Suspense } from "react";
export default function dynamic(loader: () => Promise<any>, _opts?: any) {
  const L = React.lazy(async () => ({ default: await loader() }));
  return function Dyn(props: any) { return <Suspense fallback={null}><L {...props} /></Suspense>; };
}

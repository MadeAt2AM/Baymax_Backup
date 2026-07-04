import "./index.css";
import { Composition } from "remotion";
import { MainComposition } from "./Composition";
import { Council } from "./Council";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="MainComp"
        component={MainComposition}
        durationInFrames={2700}
        fps={30}
        width={1080}
        height={1080}
      />
      <Composition
        id="Council"
        component={Council}
        durationInFrames={2100}
        fps={30}
        width={1080}
        height={1920}
      />
    </>
  );
};

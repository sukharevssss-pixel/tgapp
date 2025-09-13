// src/tabs/Fireworks.jsx (Новая, упрощенная версия с конфетти)

import React, { useEffect, useState } from "react";
import Particles, { initParticlesEngine } from "@tsparticles/react";
import { loadSlim } from "tsparticles-slim";

const Fireworks = () => {
  const [init, setInit] = useState(false);

  useEffect(() => {
    initParticlesEngine(async (engine) => {
      await loadSlim(engine);
    }).then(() => {
      setInit(true);
    });
  }, []);

  const options = {
    fullScreen: {
      zIndex: 9999,
    },
    particles: {
      number: {
        value: 0,
      },
      color: {
        value: ["#3b82f6", "#f0ad4e", "#16a34a", "#dc2626", "#ffffff"],
      },
      shape: {
        type: ["circle", "square", "triangle"],
      },
      opacity: {
        value: { min: 0, max: 1 },
        animation: {
          enable: true,
          speed: 1,
          startValue: "max",
          destroy: "min",
        },
      },
      size: {
        value: { min: 3, max: 7 },
      },
      life: {
        duration: {
          sync: true,
          value: 5,
        },
        count: 1,
      },
      move: {
        enable: true,
        gravity: {
          enable: true,
          acceleration: 20,
        },
        speed: { min: 10, max: 30 },
        decay: 0.1,
        direction: "none",
        straight: false,
        outModes: {
          default: "destroy",
          top: "none",
        },
      },
    },
    // Эмиттеры создают "взрывы" конфетти в случайных местах
    emitters: {
      direction: "none",
      rate: {
        quantity: 5,
        delay: 0.3,
      },
      position: {
        x: 50,
        y: 50,
      },
      spawnColor: {
        animation: {
          h: {
            enable: true,
            offset: {
              min: -1.4,
              max: 1.4,
            },
            speed: 0.1,
            sync: false,
          },
          l: {
            enable: true,
            offset: {
              min: 20,
              max: 80,
            },
            speed: 0,
            sync: false,
          },
        },
      },
    },
  };

  if (init) {
    return <Particles id="tsparticles" options={options} />;
  }

  return <></>;
};

export default Fireworks;

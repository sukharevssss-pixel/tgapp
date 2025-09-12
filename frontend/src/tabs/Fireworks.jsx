// src/tabs/Fireworks.jsx

import React, { useCallback } from "react";
import Particles from "react-tsparticles";
import { loadSlim } from "tsparticles-slim";

const Fireworks = () => {
  const particlesInit = useCallback(async (engine) => {
    // Инициализируем движок tsparticles
    await loadSlim(engine);
  }, []);

  // Конфигурация для эффекта салюта
  const options = {
    autoPlay: true,
    background: {
      color: {
        value: "rgba(0,0,0,0)", // Прозрачный фон
      },
    },
    fullScreen: {
      enable: true,
      zIndex: 9999, // Поверх всех остальных элементов
    },
    detectRetina: true,
    duration: 0.4, // Длительность вспышек в секундах
    fpsLimit: 120,
    emitters: [
      {
        direction: "top",
        life: {
          count: 0,
          duration: 0.1,
          delay: 0.1,
        },
        position: {
          x: 50,
          y: 100,
        },
        rate: {
          delay: 0.15,
          quantity: 1,
        },
        size: {
          width: 100,
          height: 0,
        },
      },
    ],
    particles: {
      number: {
        value: 0,
      },
      color: {
        value: ["#3b82f6", "#f0ad4e", "#16a34a", "#dc2626"], // Цвета салюта
      },
      shape: {
        type: "circle",
      },
      opacity: {
        value: { min: 0.1, max: 1 },
        animation: {
          enable: true,
          speed: 0.7,
          sync: false,
          startValue: "max",
          destroy: "min",
        },
      },
      size: {
        value: { min: 2, max: 4 },
      },
      life: {
        count: 1,
        duration: {
          value: {
            min: 0.25,
            max: 0.5,
          },
        },
      },
      move: {
        enable: true,
        gravity: {
          enable: true,
          acceleration: 20,
        },
        speed: { min: 5, max: 15 },
        decay: 0.1,
        direction: "none",
        straight: false,
        outModes: {
          default: "destroy",
          top: "none",
        },
      },
    },
    sounds: { // Можно добавить звуки!
      enable: false, // Пока выключим
    }
  };

  return <Particles id="tsparticles" init={particlesInit} options={options} />;
};

export default Fireworks;

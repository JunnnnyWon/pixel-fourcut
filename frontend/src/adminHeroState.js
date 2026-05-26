export function getAdminHeroState({ currentSession, selectedShot, activePreset, comfyOnline }) {
  if (!currentSession) {
    return {
      actionKind: 'start',
      title: '새 팀을 받을 준비가 됐어요',
      description: '버튼 하나만 누르면 다음 팀 촬영을 바로 시작할 수 있어요.',
      buttonLabel: '새 팀 시작',
      disabled: false,
    }
  }

  if (currentSession.phase === 'capturing') {
    return {
      actionKind: 'finish',
      title: '촬영이 끝났다면 다음으로 넘어가세요',
      description: '사진을 다 찍었으면 큰 버튼을 눌러 사진 고르기 단계로 이동합니다.',
      buttonLabel: '촬영 끝내기',
      disabled: false,
    }
  }

  if (currentSession.phase === 'reviewing' && !selectedShot) {
    return {
      actionKind: 'select',
      title: '마음에 드는 사진을 하나 누르세요',
      description: '아래 사진을 한 장 누르면 바로 선택됩니다.',
      buttonLabel: '먼저 사진 선택',
      disabled: true,
    }
  }

  if (currentSession.phase === 'reviewing' && selectedShot) {
    if (!activePreset) {
      return {
        actionKind: 'run',
        title: 'AI를 만들기 전에 프리셋을 활성화하세요',
        description: '아래 워크플로우 프리셋에서 하나를 활성화해야 AI 그림 만들기를 시작할 수 있습니다.',
        buttonLabel: '프리셋 활성화 필요',
        disabled: true,
      }
    }

    if (comfyOnline === null) {
      return {
        actionKind: 'run',
        title: 'ComfyUI 연결 상태를 확인하는 중입니다',
        description: '잠시 후 자동으로 다시 확인합니다. 계속 이 상태면 ComfyUI 서버를 확인하세요.',
        buttonLabel: '상태 확인 중',
        disabled: true,
      }
    }

    if (!comfyOnline) {
      return {
        actionKind: 'run',
        title: 'ComfyUI가 연결되어야 AI를 만들 수 있어요',
        description: 'ComfyUI 서버가 꺼져 있거나 연결 주소가 다를 수 있습니다. 연결되면 버튼이 자동으로 활성화됩니다.',
        buttonLabel: 'ComfyUI 연결 필요',
        disabled: true,
      }
    }

    return {
      actionKind: 'run',
      title: '이 사진으로 AI 그림을 만듭니다',
      description: '선택한 사진이 맞으면 버튼을 눌러 AI 대기열에 넣으세요.',
      buttonLabel: 'AI 그림 만들기',
      disabled: false,
    }
  }

  return {
    actionKind: 'none',
    title: '지금은 자동 진행 중이에요',
    description: '현재 팀은 대기열 또는 처리 단계에 있습니다. 다음 팀을 받을 준비를 확인하세요.',
    buttonLabel: '대기 중',
    disabled: true,
  }
}

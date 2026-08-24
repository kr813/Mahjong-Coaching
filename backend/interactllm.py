import os
import oci
from oci.generative_ai_agent_runtime import GenerativeAiAgentRuntimeClient
from oci.generative_ai_agent_runtime.models import ChatDetails, CreateSessionDetails

# AIエージェントのエンドポイントを入力
AGENT_ENDPOINT_OCID = "ocid1.genaiagentendpoint.oc1.ap-osaka-1.amaaaaaapimhcliaa726mjt7r472vztwa2bb46egb6dmsbvtsdvtfcvve4ba"
REGION = "ap-osaka-1"

def _generate_advice(parsed_data=None) -> str:
    # プロンプトはprompt.txtで受け取る
    current_dir = os.path.dirname(os.path.abspath(__file__))
    prompt_file_path = os.path.join(current_dir, "prompt.txt")
    with open(prompt_file_path, "r", encoding="utf-8") as f:
        text = f.read()

    signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()

    client = GenerativeAiAgentRuntimeClient(
        config={"region": REGION},
        signer=signer,
        service_endpoint=f"https://agent-runtime.generativeai.{REGION}.oci.oraclecloud.com"
    )

    # 1. セッション作成
    session_response = client.create_session(
        create_session_details=CreateSessionDetails(
            display_name="test-session",
            description="python sdk test session"
        ),
        agent_endpoint_id=AGENT_ENDPOINT_OCID
    )

    # Session モデルの id を利用
    session_id = session_response.data.id

    # 2. チャット実行
    chat_response = client.chat(
        agent_endpoint_id=AGENT_ENDPOINT_OCID,
        chat_details=ChatDetails(
            user_message=text,
            session_id=session_id
        )
    )

    # AIエージェントのアドバイス
    return chat_response.data.message.content.text



import json
import os

try:
    import oci
except ImportError:  # pragma: no cover - import is optional in local environments
    oci = None


def _generate_advice(json_data: dict) -> str:
    """
    JSONデータ（辞書型）を入力として受け取り、外部の prompt.txt の指示に従って
    OCI Generative AI で分析・アドバイスを生成し、純粋なテキストとして返します。
    """
    if oci is None:
        return "OCI client is not available"

    prompt_file_path = os.path.join(os.path.dirname(__file__), "prompt.txt")
    if not os.path.exists(prompt_file_path):
        return f"エラー: 指示ファイル '{prompt_file_path}' が見つかりません。"

    with open(prompt_file_path, "r", encoding="utf-8") as handle:
        system_prompt = handle.read().strip()

    # 【OCI移行時の変更点】
    # ローカル環境では ~/.oci/config を使用しますが、OCI上のComputeやFunctions等に載せる際は
    # Instance Principal や Resource Principal 等のより安全な認証方式（例: oci.auth.signers.InstancePrincipalsSecurityTokenSigner() など）
    # への書き換え、または実行環境に合わせた設定ファイルの読み込みパスに変更してください。
    config = oci.config.from_file("~/.oci/config", "DEFAULT")

    # 【OCI移行時の変更点】
    # Generative AIサービスを利用するリージョンのエンドポイントに変更してください。
    # (例: シカゴリージョン以外、あるいはDedicated AI Clusterを利用する場合など)
    endpoint = "https://inference.generativeai.us-chicago-1.oci.oraclecloud.com"
    genai_client = oci.generative_ai_inference.GenerativeAiInferenceClient(
        config=config,
        service_endpoint=endpoint,
    )

    # 【OCI移行時の変更点】
    # 実際にアドバイス生成APIを呼び出す OCI のコンパートメント OCID に必ず書き換えてください。
    compartment_id = "ocid1.compartment.oc1..your_compartment_ocid"

    # 【OCI移行時の変更点】
    # 利用する大規模言語モデル（例: cohere.command-r-plus などの別モデルや、Dedicated AI Cluster でホストしているカスタムモデル）の
    # ID または OCID に必要に応じて書き換えてください。
    model_id = "meta.llama-3-70b-instruct"
    input_json_str = json.dumps(json_data, ensure_ascii=False, indent=2)

    chat_request = oci.generative_ai_inference.models.ChatDetails(
        compartment_id=compartment_id,
        serving_mode=oci.generative_ai_inference.models.OnDemandServingMode(model_id=model_id),
        chat_request=oci.generative_ai_inference.models.GenericChatRequest(
            messages=[
                oci.generative_ai_inference.models.Message(
                    role="SYSTEM",
                    content=[oci.generative_ai_inference.models.TextContent(text=system_prompt)],
                ),
                oci.generative_ai_inference.models.Message(
                    role="USER",
                    content=[oci.generative_ai_inference.models.TextContent(text=f"分析対象のデータはこちらです:\n{input_json_str}")],
                ),
            ],
            max_tokens=600,
            temperature=0.7,
        ),
    )

    try:
        response = genai_client.chat(chat_request)
        return response.data.chat_response.choices[0].message.content[0].text
    except Exception as exc:
        return f"エラーが発生しました: {exc}"
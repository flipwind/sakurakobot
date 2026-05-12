from ..utils import *
from . import chatapi as chatapi
from . import markdown as markdown
import asyncio

whathappened = on_alconna(
    Alconna("发生了啥", Args["count?", int, 500], meta=CommandMeta(compact=True)),
    aliases=("#发生了啥", "#总结一下"),
)


@whathappened.handle()
async def _(
    event: GroupMessageEvent, bot: Bot, count: Match[int] = AlconnaMatch("count")
):
    if COMMAND_OUTPUT:
        await whathappened.send(f"Handle [#发生了啥] with count [{count.result}]")

    if count.result > 1500:
        await whathappened.send("消息过多，已限制为 1500 条消息。")
        count.result = 1500
    if count.result < 100:
        await whathappened.send("消息过少，已调整为 100 条消息。")
        count.result = 100

    # Ensure the group state exists in sakurako_state
    group_key = f"group_{event.group_id}"
    if group_key not in sakurako_state:
        sakurako_state[group_key] = {}

    if sakurako_state[group_key].get("whathappened") == "processing":
        await whathappened.finish(
            "盯——\n本喵发现本群已经有了一个总结进程，请等待该请求完成后再进行下一次请求喵。"
        )

    sakurako_state[group_key]["whathappened"] = "processing"
    
    try:
        p = await bot.call_api(
            "get_group_msg_history", group_id=event.group_id, count=count.result
        )

        await whathappened.send(
            f"知道你超急的喵。咱喵已经帮你抓到了最近 {count.result} 条消息喽，主人就乖乖在这里等本喵一下下啦，不要跑丢呜～"
        )

        all_models = [
            "gemini-3-flash-preview",
            "gemini-2.5-flash",
            "gemini-3.1-flash-lite",
            "gemini-2.5-flash-lite"
        ]
        
        current_model = None
        for i, model in enumerate(all_models):
            current_model = model
            try:
                content = await asyncio.wait_for(chatapi.summarize_chat(p, model_name=model), timeout=300)
                break
            except (asyncio.TimeoutError, Exception) as e:
                logger.error(f"调用模型 {model} 失败: {e}")
                if i + 1 < len(all_models):
                    await whathappened.send(f"五分钟过去了...模型 {model} 炸了，换一个试试喵...")
                    continue
                else:
                    content = f"呜呜，所有模型都失败了喵...\n等等再试试吧喵。"
        
        if content:
            messages = [
                f"下面是最近 {count.result} 条的总结喵。",
                content,
                f"使用 {current_model} 总结。",
            ]
            await whathappened.send(Message(MessageSegment.image(await markdown.md_to_image(content, width=800))))
            await send_node_messages(event, messages)
            
    except Exception as e:
        await whathappened.send(f"发生神秘错误了喵: {e}")
        
    finally:
        sakurako_state[group_key]["whathappened"] = "done"


whathappened_debug = on_alconna(
    Alconna("#aidebug", Args["count?", int, 500], meta=CommandMeta(compact=True))
)

@whathappened_debug.handle()
async def _(
    event: GroupMessageEvent, bot: Bot, count: Match[int] = AlconnaMatch("count")
):
    if COMMAND_OUTPUT:
        await whathappened_debug.send(f"Handle [#aidebug] with count [{count.result}]")

    p = await bot.call_api(
        "get_group_msg_history", group_id=event.group_id, count=count.result
    )
    
    p = await chatapi.format_messages(p)

    with open(f"{TEMP_PATH}/temp.txt", "w", encoding="utf-8") as f:
        f.write(p)

    await bot.send_group_msg(
        group_id=event.group_id,
        message=Message(
            MessageSegment(
            type = "file", 
            data= {"file": f"file://{TEMP_PATH}/temp.txt", "name": "temp.txt"}
        ),
        )
    )
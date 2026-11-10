"""Resolve who a question refers to and produce grounded Vietnamese answers."""

def has_color(person,color,field):
    profile=person[field]
    return profile['available'] and any(c['name']==color and c['share']>=0.22 for c in profile['colors'])

def describe(person):
    return (f"Người {person['id']} {person['position']}: áo {person['shirt']['label']}, "
            f"quần {person['pants']['label']}.")

def answer_question(analysis,plan,selected_person=None):
    people=analysis['people'];intent=plan['intent']
    result={'intent':intent,'person_ids':[],'status':'ok','answer':'','evidence':[]}
    if intent=='unsupported':
        result.update(status='unsupported',answer='Bạn có thể hỏi số người, màu áo/quần, vị trí hoặc tìm người theo màu trang phục.')
        return result
    if not people:
        result.update(status='no_people',answer='Mình chưa phát hiện được người trong ảnh này. Bạn thử ảnh rõ hơn hoặc người lớn hơn trong khung hình nhé.')
        return result
    if plan['color']=='ambiguous_green_blue':
        result.update(status='clarify',answer='Bạn muốn tìm áo/quần xanh lá hay xanh dương?')
        return result
    candidates=people[:]
    if plan['color']:
        candidates=[p for p in candidates if has_color(p,plan['color'],plan['color_field'])]
    if intent=='count':
        if plan['position']:
            key=plan['position']
            candidates=[p for p in candidates if ((p['center_x']<0.5) if key=='left' else
                        ((p['center_x']>=0.5) if key=='right' else (1/3<=p['center_x']<=2/3)))]
        result['person_ids']=[p['id'] for p in candidates]
        qualifier=f" có {plan['color_field']=='shirt' and 'áo' or 'quần'} màu {plan['color']}" if plan['color'] else ''
        result['answer']=f"Mình phát hiện {len(candidates)} người{qualifier}"+(' trong vùng bạn hỏi.' if plan['position'] else ' trong ảnh.')
        return result
    if plan['id'] is not None:
        candidates=[p for p in candidates if p['id']==plan['id']]
    elif plan['position'] and candidates:
        if plan['position']=='left':candidates=[min(candidates,key=lambda p:p['center_x'])]
        elif plan['position']=='right':candidates=[max(candidates,key=lambda p:p['center_x'])]
        else:candidates=[min(candidates,key=lambda p:abs(p['center_x']-0.5))]
    elif selected_person is not None and not plan['color'] and not plan['all']:
        candidates=[p for p in candidates if p['id']==selected_person]
    elif not plan['color'] and not plan['all'] and intent not in ('list_people','find_color') and len(candidates)>1:
        result.update(status='clarify',person_ids=[p['id'] for p in candidates],
            answer='Bạn muốn hỏi người nào? Bấm vào khung người trong ảnh hoặc nói “người số 2”, “người bên trái”.')
        return result
    if not candidates:
        result.update(status='not_found',answer='Mình chưa tìm thấy người phù hợp trong các khung đã phát hiện. Bạn có thể chọn một khung người cụ thể để kiểm tra.')
        return result
    result['person_ids']=[p['id'] for p in candidates]
    if intent in ('describe','list_people'):result['answer']='\n'.join(describe(p) for p in candidates)
    elif intent in ('location','find_color'):
        result['answer']=' '.join(f"Người {p['id']} {p['position']} ảnh." for p in candidates)
    else:
        field='pants' if intent=='pants_color' else 'shirt';label='quần' if field=='pants' else 'áo'
        sentences=[]
        for p in candidates:
            profile=p[field]
            if profile['available']:
                sentences.append(f"Người {p['id']} {p['position']} có {label} màu {profile['label']} (ước lượng từ vùng {label} trong ảnh).")
            else:
                sentences.append(f"Mình chưa xác định rõ màu {label} của người {p['id']}. {profile['reason'] or 'Vùng này có nhiều màu hoặc bị che khuất.'}")
            result['evidence'].append({'person_id':p['id'],'field':field,'region':profile['region'],
                'crop':profile['crop'],'colors':profile['colors'],'coverage':profile['coverage'],
                'available':profile['available']})
        result['answer']='\n'.join(sentences)
    return result
